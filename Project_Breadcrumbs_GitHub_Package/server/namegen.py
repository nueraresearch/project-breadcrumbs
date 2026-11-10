#!/usr/bin/env python3
"""Project Breadcrumbs — generate and assign study names (D-78).

A study name is a screened placeholder, not a globally unique identity. This
tool implements the mechanical rules:

  * a pool at least twice the fundable placement count;
  * ordinary given-name and surname combinations from the documented lists
    below, all ASCII and label-length;
  * a project-wide blocklist of people connected to the project, kept private
    and never committed;
  * one random name per deployment, not derived from the deployment id;
  * retirement after use, including cancellation and a failed host check;
  * a private deployment-to-name mapping.

It cannot know who lives at an address. The host's yes/no check remains
manual: show the name in writing, ask whether it is in use at the address, and
record the answer with `confirm`. A yes or any uncertainty retires the name and
requires a replacement.

The state file contains study names and deployment ids. Keep it in the private
operational annex and never commit it. The default path is under
`private-data/`, which the repository already ignores.

Usage:
    # from the repository root
    python3 server/namegen.py init --blocklist private-data/name_blocklist.txt
    python3 server/namegen.py issue DEP-001
    python3 server/namegen.py confirm DEP-001 --passed
    python3 server/namegen.py confirm DEP-001 --failed
    python3 server/namegen.py retire DEP-001 --reason "deployment cancelled"
    python3 server/namegen.py show
    python3 server/namegen.py status
    python3 server/namegen.py check
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from typing import Optional

STATE_VERSION = 1
DEFAULT_STATE = os.path.join("private-data", "study_names.json")
DEFAULT_BLOCKLIST = os.path.join("private-data", "name_blocklist.txt")
MAX_NAME_LENGTH = 32
MIN_POOL_MULTIPLIER = 2
POOL_SOURCE = "namegen.py/v1"

# Common given names and surnames, chosen for a broad ordinary mix rather than
# to match any particular household. The list is public; the screened pool and
# the deployment mapping are not.
GIVEN_NAMES = (
    "Alice", "Amelia", "Ana", "Andrew", "Angel", "Barbara", "Benjamin",
    "Camila", "Carlos", "Caroline", "Daniel", "David", "Diego", "Elena",
    "Ethan", "Grace", "Hannah", "Henry", "Isabel", "James", "Janet",
    "Javier", "Jennifer", "John", "Jose", "Julia", "Karen", "Laura",
    "Lucia", "Luis", "Margaret", "Maria", "Mark", "Martha", "Mateo",
    "Michael", "Nora", "Olivia", "Patricia", "Paul", "Rachel", "Robert",
    "Rosa", "Samuel", "Sarah", "Sofia", "Susan", "Thomas", "Victor",
    "William", "Yvonne",
)

SURNAMES = (
    "Adams", "Alvarez", "Anderson", "Bailey", "Baker", "Bennett", "Brooks",
    "Brown", "Campbell", "Carter", "Castillo", "Clark", "Collins", "Cook",
    "Cooper", "Cruz", "Davis", "Diaz", "Edwards", "Ellis", "Evans",
    "Foster", "Garcia", "Gomez", "Gonzalez", "Gray", "Green", "Hall",
    "Harris", "Hernandez", "Hill", "Howard", "Hughes", "Jackson",
    "Johnson", "Jones", "Kelly", "King", "Lee", "Lewis", "Lopez",
    "Martin", "Martinez", "Miller", "Mitchell", "Moore", "Morales",
    "Morgan", "Murphy", "Nelson", "Nguyen", "Ortiz", "Parker", "Perez",
    "Peterson", "Phillips", "Powell", "Price", "Ramirez", "Reed", "Reyes",
    "Richardson", "Rivera", "Roberts", "Robinson", "Rodriguez", "Ross",
    "Russell", "Sanchez", "Sanders", "Scott", "Smith", "Stewart", "Taylor",
    "Thomas", "Thompson", "Torres", "Turner", "Walker", "Ward", "Watson",
    "White", "Williams", "Wilson", "Wood", "Wright", "Young",
)


class NameGenError(Exception):
    """A study-name operation cannot be completed safely."""


def _utcnow() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _normalise(name: str) -> str:
    return " ".join(name.split()).casefold()


def load_blocklist(path: str) -> set[str]:
    """Reads one full name per line; blank lines and # comments are ignored."""
    if not os.path.exists(path):
        raise NameGenError(
            f"blocklist not found: {path}. List the full names of everyone "
            "connected to the project, one per line, and keep the file private."
        )
    blocked = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            blocked.add(_normalise(line))
    if not blocked:
        raise NameGenError(
            f"blocklist is empty: {path}. Screen project-connected names "
            "before generating a pool."
        )
    return blocked


class NamePool:
    """The private pool, its assignments, and the retired names."""

    def __init__(self, state: dict, rng: Optional[random.Random] = None):
        if not isinstance(state, dict):
            raise NameGenError("state must be a JSON object")
        if state.get("version") != STATE_VERSION:
            raise NameGenError(
                f"unsupported state version: {state.get('version')!r}; "
                f"expected {STATE_VERSION}"
            )
        for key in (
            "created_at",
            "placements",
            "pool_size",
            "pool_source",
            "available",
            "assignments",
            "retired",
        ):
            if key not in state:
                raise NameGenError(f"state is missing {key!r}")
        if not isinstance(state["placements"], int) or not isinstance(
            state["pool_size"], int
        ):
            raise NameGenError("placements and pool_size must be integers")
        if not isinstance(state["available"], list):
            raise NameGenError("available must be a list")
        if not isinstance(state["assignments"], dict):
            raise NameGenError("assignments must be an object")
        if not isinstance(state["retired"], list):
            raise NameGenError("retired must be a list")
        self.state = state
        self.rng = rng or random.SystemRandom()

    # -- creation and persistence ---------------------------------------

    @classmethod
    def create(
        cls,
        placements: int,
        pool_size: int,
        blocklist: set[str],
        rng: Optional[random.Random] = None,
    ) -> "NamePool":
        if placements < 1:
            raise NameGenError("placements must be at least 1")
        floor = MIN_POOL_MULTIPLIER * placements
        if pool_size < floor:
            raise NameGenError(
                f"pool size {pool_size} is below the D-78 floor of "
                f"{MIN_POOL_MULTIPLIER} x {placements} = {floor}"
            )
        blocked = {_normalise(name) for name in blocklist}
        if not blocked:
            raise NameGenError(
                "blocklist is empty; screen project-connected names first"
            )

        rng = rng or random.SystemRandom()
        candidates = []
        for given in GIVEN_NAMES:
            for surname in SURNAMES:
                if given == surname:
                    continue
                name = f"{given} {surname}"
                if len(name) > MAX_NAME_LENGTH or not name.isascii():
                    continue
                if _normalise(name) in blocked:
                    continue
                candidates.append(name)

        rng.shuffle(candidates)
        if len(candidates) < pool_size:
            raise NameGenError(
                f"only {len(candidates)} usable combinations after screening; "
                f"need {pool_size}"
            )

        state = {
            "version": STATE_VERSION,
            "created_at": _utcnow(),
            "placements": placements,
            "pool_size": pool_size,
            "pool_source": POOL_SOURCE,
            "available": candidates[:pool_size],
            "assignments": {},
            "retired": [],
        }
        return cls(state, rng)

    @classmethod
    def load(cls, path: str, rng: Optional[random.Random] = None) -> "NamePool":
        if not os.path.exists(path):
            raise NameGenError(f"state file not found: {path}. Run init first.")
        if os.name == "posix":
            mode = stat.S_IMODE(os.stat(path).st_mode)
            if mode & 0o077:
                print(
                    f"warning: {path} is readable by group or other; "
                    "move it to a private location",
                    file=sys.stderr,
                )
        with open(path, encoding="utf-8") as fh:
            try:
                state = json.load(fh)
            except json.JSONDecodeError as exc:
                raise NameGenError(
                    f"state file is not valid JSON: {path}: {exc}"
                ) from exc
        return cls(state, rng)

    def save(self, path: str) -> None:
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=directory, prefix=".namegen.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self.state, fh, indent=2, sort_keys=True)
                fh.write("\n")
            if os.name == "posix":
                os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    # -- assignment and retirement --------------------------------------

    @staticmethod
    def _validate_deployment(deployment_id: str) -> None:
        if not isinstance(deployment_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", deployment_id
        ):
            raise NameGenError(
                "deployment id must be 1-64 letters, digits, dots, underscores, "
                "or hyphens, starting with a letter or digit"
            )

    def _assignment(self, deployment_id: str) -> dict:
        assignment = self.state["assignments"].get(deployment_id)
        if assignment is None:
            raise NameGenError(
                f"deployment {deployment_id!r} has no study name; run issue first"
            )
        return assignment

    def issue(self, deployment_id: str) -> str:
        self._validate_deployment(deployment_id)
        assignment = self.state["assignments"].get(deployment_id)
        if assignment is not None:
            status = assignment.get("status")
            if status in ("issued", "confirmed"):
                raise NameGenError(
                    f"deployment {deployment_id!r} already has an active study name"
                )
            if status == "retired":
                raise NameGenError(
                    f"deployment {deployment_id!r} is retired; use a new deployment id"
                )
            if status != "reissue_required":
                raise NameGenError(
                    f"deployment {deployment_id!r} has an unknown status {status!r}"
                )

        if not self.state["available"]:
            raise NameGenError(
                "the pool is exhausted; do not reuse a retired name. "
                "Build a new screened pool under D-78."
            )

        name = self.rng.choice(self.state["available"])
        self.state["available"].remove(name)
        now = _utcnow()
        if assignment is None:
            assignment = {
                "name": None,
                "status": "issued",
                "host_check": None,
                "issued_at": None,
                "confirmed_at": None,
                "events": [],
            }
            self.state["assignments"][deployment_id] = assignment

        assignment.update(
            {
                "name": name,
                "status": "issued",
                "host_check": None,
                "issued_at": now,
                "confirmed_at": None,
            }
        )
        assignment.setdefault("events", []).append(
            {"at": now, "event": "issued", "name": name}
        )
        return name

    def confirm(self, deployment_id: str, passed: bool) -> dict:
        assignment = self._assignment(deployment_id)
        status = assignment.get("status")
        if status == "retired":
            raise NameGenError(f"deployment {deployment_id!r} is retired")
        if status == "reissue_required":
            raise NameGenError(
                f"deployment {deployment_id!r} is waiting for a replacement; "
                "run issue first"
            )

        if passed:
            if status == "confirmed" and assignment.get("host_check") == "passed":
                return {
                    "status": "confirmed",
                    "name": assignment.get("name"),
                    "retired": None,
                }
            if status not in ("issued", "confirmed"):
                raise NameGenError(
                    f"deployment {deployment_id!r} is not awaiting a host check"
                )
            name = assignment.get("name")
            if not name:
                raise NameGenError(
                    f"deployment {deployment_id!r} has no active study name"
                )
            now = _utcnow()
            assignment["status"] = "confirmed"
            assignment["host_check"] = "passed"
            assignment["confirmed_at"] = now
            assignment.setdefault("events", []).append(
                {"at": now, "event": "host_check_passed", "name": name}
            )
            return {"status": "confirmed", "name": name, "retired": None}

        if status not in ("issued", "confirmed"):
            raise NameGenError(
                f"deployment {deployment_id!r} is not awaiting a host check"
            )
        name = assignment.get("name")
        if not name:
            raise NameGenError(
                f"deployment {deployment_id!r} has no active study name"
            )
        now = _utcnow()
        self._retire_name(deployment_id, name, "host check failed", now)
        assignment.update(
            {
                "name": None,
                "status": "reissue_required",
                "host_check": "failed",
                "confirmed_at": None,
            }
        )
        assignment.setdefault("events", []).append(
            {"at": now, "event": "host_check_failed", "name": name}
        )
        return {"status": "reissue_required", "name": None, "retired": name}

    def retire(self, deployment_id: str, reason: str) -> str:
        reason = " ".join((reason or "").split())
        if not reason:
            raise NameGenError("a retirement reason is required")
        assignment = self._assignment(deployment_id)
        status = assignment.get("status")
        if status == "retired":
            raise NameGenError(f"deployment {deployment_id!r} is already retired")
        if status == "reissue_required":
            raise NameGenError(
                f"deployment {deployment_id!r} is waiting for a replacement; "
                "there is no active name to retire"
            )
        if status not in ("issued", "confirmed"):
            raise NameGenError(
                f"deployment {deployment_id!r} has an unknown status {status!r}"
            )
        name = assignment.get("name")
        if not name:
            raise NameGenError(
                f"deployment {deployment_id!r} has no active study name"
            )

        now = _utcnow()
        self._retire_name(deployment_id, name, reason, now)
        assignment.update({"name": None, "status": "retired", "confirmed_at": None})
        assignment.setdefault("events", []).append(
            {
                "at": now,
                "event": "retired",
                "name": name,
                "reason": reason,
            }
        )
        return name

    def _retire_name(
        self, deployment_id: str, name: str, reason: str, at: str
    ) -> None:
        self.state["retired"].append(
            {
                "name": name,
                "deployment_id": deployment_id,
                "reason": reason,
                "at": at,
            }
        )

    # -- inspection ------------------------------------------------------

    def summary(self) -> dict:
        counts = {
            "issued": 0,
            "confirmed": 0,
            "reissue_required": 0,
            "retired": 0,
        }
        for assignment in self.state["assignments"].values():
            status = assignment.get("status")
            if status in counts:
                counts[status] += 1
        return {
            "placements": self.state["placements"],
            "pool_size": self.state["pool_size"],
            "available": len(self.state["available"]),
            "issued": counts["issued"],
            "confirmed": counts["confirmed"],
            "reissue_required": counts["reissue_required"],
            "retired": len(self.state["retired"]),
            "retired_deployments": counts["retired"],
        }

    def rows(self) -> list[dict]:
        rows = []
        for deployment_id in sorted(self.state["assignments"]):
            assignment = self.state["assignments"][deployment_id]
            rows.append(
                {
                    "deployment_id": deployment_id,
                    "name": assignment.get("name") or "-",
                    "status": assignment.get("status", "?"),
                    "host_check": assignment.get("host_check") or "-",
                    "issued_at": assignment.get("issued_at") or "-",
                }
            )
        return rows

    def check(self, blocklist: Optional[set[str]] = None) -> dict:
        state = self.state
        errors = []
        placements = state["placements"]
        pool_size = state["pool_size"]

        if placements < 1:
            errors.append("placements must be at least 1")
        if pool_size < MIN_POOL_MULTIPLIER * placements:
            errors.append(
                f"pool size {pool_size} is below the D-78 floor of "
                f"{MIN_POOL_MULTIPLIER} x {placements}"
            )

        names = list(state["available"])
        for deployment_id, assignment in state["assignments"].items():
            status = assignment.get("status")
            if status not in (
                "issued",
                "confirmed",
                "reissue_required",
                "retired",
            ):
                errors.append(
                    f"{deployment_id}: unknown status {status!r}"
                )
                continue
            if status in ("issued", "confirmed"):
                name = assignment.get("name")
                if not name:
                    errors.append(f"{deployment_id}: {status} without a name")
                else:
                    names.append(name)
                if status == "confirmed" and assignment.get("host_check") != "passed":
                    errors.append(
                        f"{deployment_id}: confirmed without a passed host check"
                    )
                if status == "issued" and assignment.get("host_check") is not None:
                    errors.append(
                        f"{deployment_id}: issued with a host check already recorded"
                    )
            elif status == "reissue_required":
                if assignment.get("name") is not None:
                    errors.append(
                        f"{deployment_id}: awaiting reissue but still has a name"
                    )
                if assignment.get("host_check") != "failed":
                    errors.append(
                        f"{deployment_id}: awaiting reissue without a failed host check"
                    )
            elif status == "retired":
                if assignment.get("name") is not None:
                    errors.append(
                        f"{deployment_id}: retired but still has a name"
                    )

        for entry in state["retired"]:
            if not isinstance(entry, dict) or not entry.get("name"):
                errors.append("retired entry without a name")
            else:
                names.append(entry["name"])

        if len(names) != pool_size:
            errors.append(
                f"pool count is {len(names)}, expected {pool_size}"
            )

        string_names = [name for name in names if isinstance(name, str)]
        normalised = [_normalise(name) for name in string_names]
        if len(set(normalised)) != len(normalised):
            errors.append("a study name appears more than once")
        for name in names:
            if (
                not isinstance(name, str)
                or not name.isascii()
                or len(name) > MAX_NAME_LENGTH
            ):
                errors.append(
                    f"name is not ASCII or exceeds {MAX_NAME_LENGTH} "
                    f"characters: {name!r}"
                )

        if blocklist:
            blocked = {_normalise(name) for name in blocklist}
            for name in string_names:
                if _normalise(name) in blocked:
                    errors.append(f"name is on the blocklist: {name}")

        if errors:
            raise NameGenError("; ".join(errors))

        result = self.summary()
        if result["available"] == 0:
            result["warning"] = "pool exhausted; no further names can be issued"
        return result


# -- command line --------------------------------------------------------


def _cmd_init(args) -> None:
    if os.path.exists(args.state) and not args.force:
        raise NameGenError(
            f"state already exists: {args.state}; use --force only to replace it"
        )
    if os.path.exists(args.state):
        print(
            f"warning: replacing {args.state}; the previous mapping will be lost",
            file=sys.stderr,
        )
    blocklist = load_blocklist(args.blocklist)
    pool_size = (
        args.pool_size
        if args.pool_size is not None
        else MIN_POOL_MULTIPLIER * args.placements
    )
    pool = NamePool.create(args.placements, pool_size, blocklist)
    pool.save(args.state)
    print(
        f"Created {pool_size} study names for {args.placements} placements."
    )
    print(f"State: {args.state} (private; do not commit).")


def _cmd_issue(args) -> None:
    pool = NamePool.load(args.state)
    name = pool.issue(args.deployment_id)
    pool.save(args.state)
    print(f"{args.deployment_id} -> {name}")
    print("Host check: show the name in writing and ask the one yes/no question.")
    print(
        f"  passed: python3 {sys.argv[0]} confirm {args.deployment_id} --passed"
    )
    print(
        f"  failed: python3 {sys.argv[0]} confirm {args.deployment_id} --failed"
    )
    print("A failed check retires the name; run issue again for a replacement.")


def _cmd_confirm(args) -> None:
    pool = NamePool.load(args.state)
    result = pool.confirm(args.deployment_id, passed=args.passed)
    pool.save(args.state)
    if result["status"] == "confirmed":
        print(
            f"Host check passed for {args.deployment_id} ({result['name']})."
        )
    else:
        print(
            f"Host check failed for {args.deployment_id}; "
            f"retired {result['retired']}."
        )
        print("Run issue again for a replacement name.")


def _cmd_retire(args) -> None:
    pool = NamePool.load(args.state)
    name = pool.retire(args.deployment_id, args.reason)
    pool.save(args.state)
    print(f"Retired {name} for {args.deployment_id}.")


def _cmd_show(args) -> None:
    pool = NamePool.load(args.state)
    print(
        "Private mapping: do not paste names or deployment ids into public "
        "material.",
        file=sys.stderr,
    )
    print(
        f"{'DEPLOYMENT':<18} {'NAME':<30} {'STATUS':<17} "
        f"{'HOST CHECK':<10} ISSUED"
    )
    for row in pool.rows():
        print(
            f"{row['deployment_id']:<18} {row['name']:<30} "
            f"{row['status']:<17} {row['host_check']:<10} {row['issued_at']}"
        )


def _cmd_status(args) -> None:
    pool = NamePool.load(args.state)
    s = pool.summary()
    print(f"Placements: {s['placements']}; pool: {s['pool_size']} names")
    print(
        f"Names: {s['available']} available, {s['issued']} issued, "
        f"{s['confirmed']} confirmed, {s['retired']} retired"
    )
    print(
        f"Deployments: {s['issued']} issued, {s['confirmed']} confirmed, "
        f"{s['reissue_required']} awaiting reissue, "
        f"{s['retired_deployments']} retired"
    )


def _cmd_check(args) -> None:
    pool = NamePool.load(args.state)
    blocklist = load_blocklist(args.blocklist) if args.blocklist else None
    result = pool.check(blocklist)
    print(
        f"OK: pool {result['pool_size']} for {result['placements']} "
        f"placements; {result['available']} available."
    )
    if result.get("warning"):
        print(f"warning: {result['warning']}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and assign screened study names under D-78. The state "
            "file and blocklist are private; never commit them."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="build a screened pool")
    p_init.add_argument("--state", default=DEFAULT_STATE)
    p_init.add_argument("--blocklist", default=DEFAULT_BLOCKLIST)
    p_init.add_argument("--placements", type=int, default=30)
    p_init.add_argument(
        "--pool-size",
        type=int,
        default=None,
        help="defaults to twice the placement count (D-78)",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="replace an existing state file; destroys the old mapping",
    )
    p_init.set_defaults(func=_cmd_init)

    p_issue = sub.add_parser("issue", help="assign a name to a deployment")
    p_issue.add_argument("deployment_id")
    p_issue.add_argument("--state", default=DEFAULT_STATE)
    p_issue.set_defaults(func=_cmd_issue)

    p_confirm = sub.add_parser(
        "confirm", help="record the host's study-name check"
    )
    p_confirm.add_argument("deployment_id")
    check = p_confirm.add_mutually_exclusive_group(required=True)
    check.add_argument("--passed", action="store_true")
    check.add_argument("--failed", action="store_true")
    p_confirm.add_argument("--state", default=DEFAULT_STATE)
    p_confirm.set_defaults(func=_cmd_confirm)

    p_retire = sub.add_parser(
        "retire", help="retire the active name for a deployment"
    )
    p_retire.add_argument("deployment_id")
    p_retire.add_argument("--reason", required=True)
    p_retire.add_argument("--state", default=DEFAULT_STATE)
    p_retire.set_defaults(func=_cmd_retire)

    p_show = sub.add_parser("show", help="print the private mapping")
    p_show.add_argument("--state", default=DEFAULT_STATE)
    p_show.set_defaults(func=_cmd_show)

    p_status = sub.add_parser("status", help="counts without names")
    p_status.add_argument("--state", default=DEFAULT_STATE)
    p_status.set_defaults(func=_cmd_status)

    p_check = sub.add_parser("check", help="validate the pool and mapping")
    p_check.add_argument("--state", default=DEFAULT_STATE)
    p_check.add_argument("--blocklist", default=DEFAULT_BLOCKLIST)
    p_check.set_defaults(func=_cmd_check)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except NameGenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
