# Project Breadcrumbs

**A Community Safety Research Pilot by Nuera Research and Developmental Laboratories**  
*Following patterns others miss.*

> **The goal isn't to catch people. The goal is to understand the system.**

Project Breadcrumbs is a proposed, voluntary community research initiative exploring whether low-cost, reusable monitoring packages can help characterize theft-related events, movement, recovery, and deployment outcomes over repeated porch deployments.

This repository contains the current concept definition, preliminary hardware requirements, camera subsystem proposal, draft pilot protocol, data model, validation plan, and open decisions.

## Status

**Proposal / pre-prototype. No pilot has launched.** No funding has been requested and no participants are currently being recruited. Hardware performance, costs, legal requirements, and research value have not yet been validated.

## Repository guide

- [`docs/PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) — purpose, problem, scope, and research questions
- [`docs/hardware/HARDWARE_REQUIREMENTS.md`](docs/hardware/HARDWARE_REQUIREMENTS.md) — preliminary module requirements and architecture
- [`docs/hardware/CAMERA_SUBSYSTEM.md`](docs/hardware/CAMERA_SUBSYSTEM.md) — camera inside the sealed box, light-triggered three-frame capture, release standard
- [`docs/hardware/PRELIMINARY_BOM.md`](docs/hardware/PRELIMINARY_BOM.md) — component categories, cost status, and unknowns
- [`docs/hardware/COST_REDUCTION_PLAN.md`](docs/hardware/COST_REDUCTION_PLAN.md) — part selections, the route from ~$156 to ~$86 per module, and the cost floor
- [`docs/pilot/PILOT_PROTOCOL_DRAFT.md`](docs/pilot/PILOT_PROTOCOL_DRAFT.md) — proposed 90-day pilot framework built from 30-day deployment cycles
- [`docs/pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md`](docs/pilot/PRE_REGISTRATION_ANALYSIS_PLAN.md) — primary outcome, event definitions, exclusion rules, and analysis fixed before data collection
- [`docs/pilot/POST_OFFICE_DATA_REQUEST.md`](docs/pilot/POST_OFFICE_DATA_REQUEST.md) — request letter and agreement terms for aggregate route volume
- [`docs/pilot/PILOT_SCALE_OPTIONS.md`](docs/pilot/PILOT_SCALE_OPTIONS.md) — cost and evidence at three, six, and ten modules
- [`docs/pilot/DEPLOYMENT_AND_OPERATIONS.md`](docs/pilot/DEPLOYMENT_AND_OPERATIONS.md) — voluntary homeowner deployment and operating cycle
- [`docs/pilot/TEST_AND_VALIDATION_PLAN.md`](docs/pilot/TEST_AND_VALIDATION_PLAN.md) — bench and field validation plan
- [`docs/data/DATA_MODEL.md`](docs/data/DATA_MODEL.md) — event and deployment data definitions
- [`docs/governance/PRIVACY_SAFETY_AND_REVIEW.md`](docs/governance/PRIVACY_SAFETY_AND_REVIEW.md) — privacy, safety, legal review, and data governance
- [`docs/governance/THREAT_MODEL.md`](docs/governance/THREAT_MODEL.md) — adversarial threats, trust boundaries, communications tiers, stop rules
- [`docs/governance/DATA_PROTECTION_CONTROLS.md`](docs/governance/DATA_PROTECTION_CONTROLS.md) — access control, encryption and key custody, retention, breach response, law-enforcement position
- [`docs/design/HARDENING_PLAN.md`](docs/design/HARDENING_PLAN.md) — proposed engineering and methods changes, acceptance thresholds, cost realism
- [`docs/design/OPEN_ITEMS.md`](docs/design/OPEN_ITEMS.md) — consolidated register of everything still undefined, by what it blocks
- [`docs/design/CONNECTIVITY_OPTIONS.md`](docs/design/CONNECTIVITY_OPTIONS.md) — cellular versus no-radio recover-to-collect, with costs and what each can measure
- [`docs/design/RADIO_AND_SIM_OPTIONS.md`](docs/design/RADIO_AND_SIM_OPTIONS.md) — what the town decides, spectrum and certification, and SIM provider comparison
- [`docs/review/DESIGN_REVIEW_R1.md`](docs/review/DESIGN_REVIEW_R1.md) — independent desk review of this package, with findings and readiness criteria
- [`DECISION_LOG.md`](DECISION_LOG.md) — confirmed decisions, proposals, and unresolved questions

## Important interpretation

The project is a research proposal, not a validated theft-prevention product, law-enforcement tool, or guarantee of recovery. A camera event does not establish identity, intent, or criminal conduct. Data should be interpreted cautiously and reported in aggregate.

All deployments must be voluntary and authorized by the participating property owner. Before any field use, the project must complete appropriate legal, privacy, safety, and insurance review for the actual deployment locations and operating procedures.

## Initial pilot concept

The proposal currently describes:
- 90-day duration, run as three 30-day deployment cycles per module
- 10 reusable modules to start, each serving three cycles
- 30 deployment cycles in total, one per volunteer host (D-53)
- Preliminary budget target of $600–$900, retained as a target rather than a budget (D-51)
- Monte Vista, Colorado as the initial site, subject to town-meeting approval (D-43)

These are planning targets from the concept proposal, not validated estimates. Feasibility must be checked against the final hardware, communications plan, incentives, insurance, and operating costs. The cost realism section of the hardening plan puts this scope at roughly $3k–$5.5k excluding labour if legal review is pro bono, or $4.8k–$9k if counsel has to be paid, so the gap against the target is expected to be wide.

## Design review status

An independent desk review of the Revision 1.0 package is recorded in [`docs/review/DESIGN_REVIEW_R1.md`](docs/review/DESIGN_REVIEW_R1.md). Its conclusion was that the concept is worth prototyping but was not ready to field, with five blocking findings. The review's recommendations were entered in the decision log as D-11 to D-26 and **were all resolved by the project owner on 2026-10-30**: see §F of [`DECISION_LOG.md`](DECISION_LOG.md) for each outcome, including the four that were rejected. The blocking finding on trigger architecture was withdrawn after the owner corrected the physical assumptions behind it.

| Revision | Date | Change |
|---|---|---|
| 1.0 | — | Initial concept package |
| 1.1 (review) | 2026-10-30 | Added design review, threat model, data protection controls, and hardening plan; no change to confirmed direction |
| 1.2 | 2026-10-30 | Owner decisions D-27 to D-51 recorded; hardware and camera documents aligned to sealed-box geometry, 30-day cycles, cellular telemetry, and public release |
| 1.3 | 2026-10-30 | Pilot protocol and README moved to 30-day cycles and 15–30 deployments; location publication precision, caption standard, and the Monte Vista, Colorado setting confirmed |
| 1.4 | 2026-10-30 | Primary outcome fixed (D-47); publication rules for minors and unconnected persons fixed (D-52) |
| 1.5 | 2026-10-30 | Starting quantity fixed at 10 modules, giving 30 deployment cycles; Monte Vista's population recorded as a sample characteristic |
| 1.6 | 2026-10-30 | Collection and return moved to the project base (D-55); study reframed as theft-event analysis against exposure rather than site sampling; post office delivery-volume context proposed (D-56) |
| 1.7 | 2026-10-30 | Added the postal data request letter and agreement terms for aggregate route volume |
| 1.8 | 2026-10-30 | Added the open items register; consolidated every undefined decision, task, and external dependency |
| 1.9 | 2026-10-30 | Technical build items decided (D-57 to D-65); per-module cost reduced from ~$156 to ~$99 |
| 1.10 | 2026-10-30 | Further trims adopted (D-66, D-67); per-module cost now ~$86, with the cost floor documented |
| 1.11 | 2026-10-30 | Added a comparison of cellular and no-radio recover-to-collect designs, with a staged recommendation |
| 1.12 | 2026-10-30 | Cellular retained for the main pilot (D-68); community Wi-Fi alternative evaluated and rejected |
| 1.13 | 2026-10-30 | Added the radio, spectrum, and SIM analysis; pilot SIM moved to Hologram (D-69) |
| 1.14 | 2026-10-30 | Added pilot scale options: what three modules cost and what they can prove |
| 1.15 | 2026-10-30 | Deployment is rolling: all modules out on day one, recovered modules reset and redeployed at a new address (D-70) |
| 1.16 | 2026-10-30 | Three-module run capped at a hard $1,000 (D-71); costed at nine modules with four recovery fees |
| 1.17 | 2026-10-30 | Run ends when money or time runs out; no fixed sample size, with a reserve floor and censoring rule (D-72) |
| 1.18 | 2026-10-30 | Pilot target raised to $2,500 for ten modules and thirty placements (D-73) |
| 1.19 | 2026-10-30 | Recovery payment set at a flat $20, no questions asked (D-74); pilot build falls to $2,298 |

## Contribution and revision policy

Treat requirements marked **Proposed** or **To validate** as provisional. Update the decision log when a design decision is approved. Do not describe a feature as implemented or tested until evidence is recorded in the repository.
