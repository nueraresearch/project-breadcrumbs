# Design Review R1 — Project Breadcrumbs

**Review date:** 2026-10-30
**Documents reviewed:** every Revision 1.0 document in this repository (README, `DECISION_LOG.md`, `PROJECT_OVERVIEW.md`, `HARDWARE_REQUIREMENTS.md`, `CAMERA_SUBSYSTEM.md`, `PRELIMINARY_BOM.md`, `PILOT_PROTOCOL_DRAFT.md`, `DEPLOYMENT_AND_OPERATIONS.md`, `TEST_AND_VALIDATION_PLAN.md`, `DATA_MODEL.md`, `PRIVACY_SAFETY_AND_REVIEW.md`)
**Status:** Desk review of written design only. No hardware, firmware, or field data existed to review. Every finding is conditional on that limitation.

## 1. Summary judgement

This is an unusually disciplined pre-prototype package. It separates confirmed direction from proposal, refuses to invent performance figures, and states its own interpretation limits before anyone is tempted to over-read a result. Most concept documents at this stage do none of those things.

The weakness is almost the inverse of the strength. The design is rigorous where it is *cautious* and thin where it is *specific*. Nearly every mechanism that would determine whether the pilot yields valid, defensible data is either undecided or under-specified: the trigger, the communications posture, retention, the legal basis, cost, the statistics, and the stop rules. Caution in prose has been substituted for decisions in design.

**Judgement: worth prototyping, not ready to field.** Two of the five blocking findings are architectural — they change what gets built. Discovering them after the BOM and enclosure are locked would be expensive, which is the main argument for doing this review now rather than at Phase 1.

## 2. Severity definitions

| Level | Meaning |
|---|---|
| **Blocking** | Must be resolved before any field deployment. Cannot be deferred to post-pilot analysis. |
| **Major** | Must be resolved before Phase 2 onboarding or before the sample grows. |
| **Minor** | Should be fixed opportunistically; not gating. |

## 3. Findings register

| ID | Sev | Area | Finding |
|---|---|---|---|
| B-01 | Withdrawn | Trigger | Premise was incorrect. The camera sits inside the sealed box and cannot see a removal; removal is observed through location telemetry (D-32). Night blindness accepted as a scope limit (D-30). |
| B-02 | Blocking | Method | The primary observation is lost exactly when it matters: an unrecovered device is both the outcome of interest and the case where on-device images are unreachable. |
| B-03 | Blocking | Governance | Retention, access, and breach procedures are named as prerequisites but left blank. A pilot cannot be launched against an unspecified default. |
| B-04 | Blocking | Legal/ethics | The lawful basis for photographing non-consenting people, and the project's position on law-enforcement requests, are both undefined. Both determine consent text, insurance, and participant risk. |
| B-05 | Blocking | Safety | Battery thermal behaviour in a sun-exposed porch package is unaddressed, and the plan implies a rechargeable pack inside a sealed enclosure without a chemistry decision or a thermal test. |
| M-01 | Major | Budget | The $600–$900 target is roughly an order of magnitude below a realistic cost for the described scope. |
| M-02 | Major | Validity | No control arm and no pre-registration. The design cannot separate induced theft from baseline theft, and cannot defend its analysis against post-hoc selection. |
| M-03 | Major | Ethics | The reward insert is simultaneously a deanonymization channel, an inducement to theft, and a contaminant of the recovery data it is meant to measure. |
| M-04 | Major | Opsec | The public repository documents the device in enough detail to defeat it. No policy governs what may be published about the hardware. |
| M-05 | Major | Security | "Local encrypted image storage" is unspecified. Without a key architecture, theft of the device is equivalent to disclosure of the images. |
| M-06 | Major | Capture | The 0 / 1 / 2.5 s burst assumes a camera warm enough to capture in under a second, and the battery budget required to keep it warm is not acknowledged. |
| M-07 | Major | Statistics | 30 cycles across 30 host households. One deployment per host removes repeated-measures clustering, which softens this finding, but self-selection still clusters households geographically and per-cycle percentages remain overconfident. |
| M-08 | Major | Readiness | No numeric go/no-go thresholds exist. The documents correctly flag the gap and then do not close it, which means "ready" is currently a matter of opinion. |
| M-09 | Major | Compliance | Certification, carrier onboarding, and battery transport requirements are absent from the BOM and from the schedule. |
| M-10 | Major | Governance | No stop rules. There is no defined condition under which the pilot pauses itself. |
| M-11 | Major | Participant risk | Participants are not warned that keeping a device on their property may attract retaliation, or that a captured event may make their household a witness in a criminal matter. |
| M-12 | Major | Test | The test plan omits thermal soak, drop/impact, enclosure seal integrity, and RF coexistence with the camera and storage. |
| m-01 | Minor | Repo | The design of record lives inside a zip archive rather than at the repository root. |
| m-02 | Minor | Privacy | No data-flow diagram, so the privacy claims cannot be audited against an implementation. |
| m-03 | Minor | Data | Timestamp policy has no maximum acceptable drift and no resynchronisation rule. |
| m-04 | Minor | Data | Event taxonomy lacks tamper, thermal, storage-full, clock-resync, and firmware-fault events. |
| m-05 | Minor | Firmware | No update, rollback, or signed-image requirement, so device state cannot be proven. |
| m-06 | Minor | Lifecycle | No end-of-study device disposition or provable data destruction step. |
| m-07 | Minor | Consent | "What happens to data already collected" is listed as a question to answer rather than defined. |
| m-08 | Minor | Minors | No specific handling rule for images that include a child. |
| m-09 | Minor | Data | No global image identifier, so redeployment across modules risks key collisions. |
| m-10 | Minor | Process | No revision history table in the README, so readers cannot tell what changed between revisions. |

## 4. Blocking findings in detail

### B-01 — The trigger defines the study, and it is aimed at the rarer event

**Resolved 2026-10-30 — finding withdrawn.** This finding assumed the camera could observe a removal. It cannot: the camera sits inside the sealed package and is occluded until the lid opens (D-27). Removal is instead observed through location telemetry (D-32), which the design now includes. The original text is retained below for the record.

The architecture assumes a person opens the package on the porch. In practice, the common pattern is lift-and-carry: the package is taken and opened elsewhere. A light-triggered camera inside a closed package has nothing to observe in that case. The pilot would therefore systematically miss the majority of its own subject matter and report a recovery rate over a sample that excludes many of the thefts that actually occurred.

The night case compounds it. A package on a dark porch that is opened releases very little light into the interior, so sensitivity is lowest exactly when opportunity is highest. Supplemental illumination solves it only by making the device visible.

**Recommendation — superseded 2026-10-30.** The owner rejected the inertial trigger (D-31). The camera cannot photograph a removal from inside a sealed box, and an inertial trigger would have produced three frames of a closed lid. The underlying concern, that losses are otherwise invisible, is addressed by location telemetry (D-32) instead. See [`../design/HARDENING_PLAN.md`](../design/HARDENING_PLAN.md) §2.

### B-02 — Privacy and validity pull in opposite directions, and the design has not chosen

If images never leave the device, the strongest privacy posture is achieved and the primary observation is destroyed the moment the device is taken. If images do leave, a compromised or misconfigured device becomes a remote camera in someone's front garden.

This is the central design tension of the project and it is not currently visible anywhere in the documents. It should be an explicit, recorded decision with a stated rationale, because every downstream choice — radio, power, cost, consent text, breach exposure — depends on it.

**Recommendation:** split the channel. Transmit *event metadata only* (time, module ID, trigger class, coarse state) and keep images on-device until physical recovery. This preserves the recovery-time observation without creating a remote imaging capability. See [`../governance/THREAT_MODEL.md`](../governance/THREAT_MODEL.md) §6 for the three-tier comparison.

### B-03 — Retention and access are the load-bearing controls and they are empty

`PRIVACY_SAFETY_AND_REVIEW.md` §6 correctly states that a retention schedule "must be approved before field deployment" and then does not contain one. In practice a blank requirement is not filled in during the rush before launch; it is filled in by whatever the first implementer finds convenient. The same applies to access control and breach response.

**Recommendation:** ship conservative defaults now, labelled as defaults, so there is a safe fallback that a future decision can only tighten. See [`../governance/DATA_PROTECTION_CONTROLS.md`](../governance/DATA_PROTECTION_CONTROLS.md) §5.

### B-04 — Two unresolved legal positions determine the whole participant relationship

First, the lawful basis for photographing people who cannot consent. Property-owner authorization does not supply it, and the documents say so correctly, but the project then proceeds without resolving it.

Second, the project's position on law-enforcement requests. The phrase "requests from an authority or third party for data" appears in the incident list with no policy behind it. This is not a detail: if images can reach a prosecutor, participants become witnesses, may be subpoenaed, and may face retaliation, and the consent form has to say so. If they cannot, that constraint needs to be engineered in, not promised.

**Recommendation:** record both positions as decisions, with counsel, before Phase 2. Data Protection Controls §7 proposes a research-only default.

### B-05 — A sealed enclosure in direct summer sun is a battery problem before it is an electronics problem

A dark package on a porch in summer can exceed 60 °C internally. A rechargeable lithium pack in that environment, with no venting path and no thermal cut-off, is a fire and injury risk that no amount of careful data governance offsets. The test plan currently mentions "temperature exposure" in general terms only.

**Recommendation:** choose chemistry for safety rather than energy density, avoid in-enclosure charging entirely, and make a thermal soak test a gating acceptance criterion. See HARDENING_PLAN §4 and AT-10 in §10.

## 5. What the package gets right and should keep

- The separation of owner-confirmed direction from engineering proposal is the single best feature of the repository. Preserve it; it is why this review can be specific.
- "A sensor trigger is not proof of theft" appears in every document that touches interpretation. That consistency prevents the most likely misuse of the results.
- The out-of-scope list is doing real work. It rules out identification and confrontation before any hardware exists, which is the correct order.
- Refusing to publish performance figures without measurement, and refusing causal language, are both correct and rarer than they should be.
- The decision log's change-control section is adequate. It is the right place for the decisions this review proposes.

## 6. Ten questions the owner must answer before Phase 1

1. Is the pilot's purpose *methods feasibility* or *incident characterization*? The answer changes the sample, the control arm, and whether images are needed at all.
2. If a device is taken, is recovering an image of the person essential — or is the recovery-time observation sufficient?
3. Will the project hand images to law enforcement on request, only on legal compulsion, or never? This must be decided, not discovered later.
4. If a participant's images identify a neighbor or a delivery worker, what is the deletion rule, and who decides?
5. Is the reward insert worth its cost in data quality and anonymity? What happens to the recovery metric if it is removed?
6. Who is the accountable data controller, by name, and who is the deputy?
7. Is a control arm of inert packages acceptable to participants and affordable?
8. What single result would justify a larger study, and what result would justify stopping?
9. Is there an ethics body willing to review this, and has it been asked?
10. What is the maximum acceptable per-cycle cost, given that the current target is off by roughly an order of magnitude?

## 7. Definition of ready

The pilot should not begin field deployment until all of the following are true and recorded in this repository:

- [x] B-01 closed 2026-10-30: camera occluded until opening (D-27); removal observed via location telemetry (D-32); night blindness accepted as a scope limit (D-30).
- [ ] B-02 resolved: communications tier chosen and documented.
- [ ] B-03 resolved: retention, access, and breach procedures exist as approved documents.
- [ ] B-04 resolved: legal basis and law-enforcement position recorded, with counsel sign-off.
- [ ] B-05 resolved: battery chemistry, charging model, and thermal acceptance test are decided.
- [ ] M-02 addressed: control arm and pre-registered analysis plan exist.
- [ ] M-08 closed: numeric thresholds approved from HARDENING_PLAN §10.
- [ ] M-10 closed: stop rules adopted and an accountable lead named.
- [ ] Costed BOM replaces the ROM estimate in HARDENING_PLAN §13.
- [ ] Every threshold has a named measurement method and a recorded result.

Until then, the correct status line for this project is the one it already uses: **proposal, not validated.**
