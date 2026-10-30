# Connectivity Options — Cellular, Recover-to-Collect, or Both

**Status:** Options analysis. Not a decision. Choosing the no-radio model would change D-33, D-47, D-53 and HW-25/26.
**Related:** [`../hardware/COST_REDUCTION_PLAN.md`](../hardware/COST_REDUCTION_PLAN.md), [`../../DECISION_LOG.md`](../../DECISION_LOG.md)

## 1. The question worth asking

Every design so far assumes a cellular radio. That radio is the largest remaining line in the build — about $32 of the $66 parts, plus a $14 SIM — and it is the only reason the module needs certification, coverage testing, and a data platform before the first deployment.

Removing it is the last big cost cut available. It is also the one that changes what the study can see.

## 2. Three architectures

### A. Cellular — the current design

The module records events, transmits them over LTE-M, and reports location. Cost is ~$86 per deployable module, and the pilot runs 30-day cycles across 30 hosts.

### B. No radio — recover to collect

The module records to internal flash and is read only when it comes back. No modem, no SIM, no antenna, no location. Cost is ~$43 per deployable module.

Because there is no radio drawing power, a 90-day cycle is comfortable on the same cell — so ten modules could run one cycle each across **ten hosts**, not thirty.

### C. Staged hybrid

Two or three no-radio units first, to validate the trigger, the camera, the seal, and the recovery workflow. Then the ten-unit cellular pilot as designed. Validation cost: about $130.

## 3. Cost

| | A. Cellular | B. No radio |
|---|---:|---:|
| Parts per module | ~$66 | **~$33** |
| Per deployable module, with spares | ~$86 | **~$43** |
| Ten modules | ~$860 | **~$430** |
| SIM, ten devices | $140 | $0 |
| Hosts to recruit | 30 | 10 |
| Cycle length | 30 days | 90 days possible |
| Certification and coverage work | Required | None |

No-radio parts: ESP32-S3 board $12, light sensor $2, accelerometer $1, reed switch $1, 18650 LiFePO4 with holder and protection $9, foam $2, retail box $2, wiring and misc $4.

## 4. What each model can actually measure

| Question | A. Cellular | B. No radio |
|---|---|---|
| When a package was opened | Yes, always | Only if the module returns |
| When a package was removed | Yes, always | Only if the module returns |
| Where a package went | Yes | **No** |
| Displacement after removal | Yes | **No** |
| Openings in packages never recovered | Yes | **No data at all** |
| Recovery rate | Yes | Yes |
| Recruitment burden | 30 hosts | 10 hosts |
| Privacy exposure | Radio transmits | Nothing transmits |
| Remote imaging risk | Architecturally excluded | Impossible |

## 5. The selection problem, stated plainly

Under B, the deployments that matter most produce nothing. A box taken and never seen again yields no timestamp, no images, and no location — the volunteer reports it gone, and that is the entire record.

So B does not sample theft. It samples **theft where the device came back**, which selects for the least determined opener, the one who discarded the box nearby or responded to the reward insert. The study would then describe that subset and, unless it were very careful, imply it described theft.

That is not a reason to reject B. It is a reason to be explicit that B answers a different question: *what happens when a box is opened and the module is recovered*, not *what happens to packages*.

## 6. What B genuinely does better

- **Half the cost**, and no SIM line at all.
- **Ten hosts instead of thirty**, one 90-day deployment each. This removes the largest logistical risk in the current design.
- **No coverage dependency.** No address in Monte Vista can fail to report.
- **No certification work**, because there is no radio to certify.
- **Stronger privacy.** Nothing is transmitted; images stay encrypted inside a sealed box until an operator opens it. "No remote imaging path" stops being an architectural claim and becomes a physical fact.
- **Longer cycles.** Without modem bursts, six months on one cell is plausible, which means fewer handoffs and less disturbance.

## 7. The bet B makes

B's entire dataset depends on reward-driven recovery working on people who open packages not addressed to them. If they keep the device, or destroy it, you learn nothing.

That is testable and worth knowing. But it is a behavioural assumption about the exact population under study, and the current design does not rely on it.

## 8. Recommendation

**Take the staged path.** Run Phase 0 on two or three no-radio units.

The three measurements that could kill the design — sleep current, time from light step to first frame, and whether a face is legible at one metre — need no radio. Testing them on a $43 unit rather than an $86 one is straightforwardly better, and it validates the seal, the arming procedure, and the recovery workflow while you are at it.

Then decide A or B for the main pilot with real numbers in hand. If the camera works and the recovery rate looks reasonable in a small trial, B becomes defensible on cost. If the camera is marginal or modules do not come back, A is the only design that can still answer the question.

## 9. If B is chosen for the main pilot

These would have to change, and the study becomes a different one:

| Item | Consequence |
|---|---|
| D-33 (cellular, all records transmitted) | Reversed |
| D-47 (time-to-removal survival) | Cannot stand: removal times are missing for the devices that never return. Replace with recovery rate and a recovered-case series |
| D-53 (30 hosts, 30-day cycles) | Becomes 10 hosts on 90-day cycles |
| HW-25 (location on movement) | Removed |
| HW-26 (cellular transmission) | Removed |
| D-58, D-59 (BG95, 1NCE) | Removed |

The primary outcome would become something like: *among packages that were opened, what proportion of modules were recovered, and what did the recovered cases show?* That is a legitimate and cheap study. It is not the theft study.

## 10. The cost of choosing badly

Buying ten cellular units before validating the camera risks $860 on unproven optics. Buying ten no-radio units for the main study risks a dataset that cannot answer the primary question at all.

The staged path spends about $130 to avoid both. Given the remaining unknowns are all in the camera and power path, that is the cheapest decision on the table.
