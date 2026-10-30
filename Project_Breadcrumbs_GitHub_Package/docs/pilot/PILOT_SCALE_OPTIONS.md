# Pilot Scale Options — 3, 6, or 10 Modules

**Status:** Analysis. No decision recorded; see open item D-04.
**Related:** D-53, D-65, [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md), [`../hardware/COST_REDUCTION_PLAN.md`](../hardware/COST_REDUCTION_PLAN.md)

## 1. The question

Ten modules is the planned pilot. Three is the smallest number that can prove the system works end to end. The gap between them is worth understanding before spending anything, because most of the cost is not per-module.

## 2. Cost at each scale

| | 3 modules | 6 modules | 10 modules |
|---|---:|---:|---:|
| Modules at ~$86 | 258 | 516 | 860 |
| Retail boxes, one per deployment | 18 | 54 | 60 |
| Connectivity, Hologram, 90 days | 19 | 37 | 63 |
| Legal review, pro bono target | 0 | 0 | 0 |
| Ethics review | 0–2,000 | 0–2,000 | 0–2,000 |
| Shipping and insurance | 100 | 200 | 400 |
| Materials and ops kit | 75 | 100 | 150 |
| Hosting and tooling | 100 | 150 | 200 |
| Contingency, 20% | ~115–460 | ~210–610 | ~350–750 |
| **Total, ethics waived** | **~$700** | **~$1,300** | **~$2,100** |
| **Total, ethics at $2,000** | **~$3,100** | **~$3,700** | **~$4,500** |

The pattern worth noticing: **the marginal cost of going from three modules to ten is about $1,400, not 3.3 times the total.** Legal and ethics review are fixed, shipping and tooling scale weakly, and the hardware itself is the smallest part of the programme.

So a three-unit pilot saves roughly $1,400 now, and costs that same $1,400 later if you scale up. What it buys is not money in the long run; it buys **sequencing**.

## 3. What three modules can prove

- The light trigger fires on a real porch, in real daylight and porch light.
- The camera captures a face that a human adjudicator can actually recognise at the opening.
- The seal survives thirty days of weather, and the module is still inside when it is opened.
- The volunteer workflow works: collect from the base, place, live with it, return.
- Cellular attaches and uploads from a real address, not a bench.
- The data platform ingests what arrives, and the publication filters apply.
- The reward insert gets a module back at least once.

Those are the seven things most likely to be wrong, and three units can expose every one of them.

## 4. What three modules cannot prove

- **Any rate.** Nine deployments — or three, if each module runs one cycle — is a case series, not an estimate.
- **The primary outcome.** A survival curve needs removal events. Three modules may produce none, and a median from zero events is not a median.
- **Recovery rate.** With n=3, one return versus two is not a finding, it is an anecdote with a percentage sign.
- **Neighbourhood pattern.** Three porches are three porches.

A three-unit trial should be reported as an **engineering and operations report**, not as study results. That distinction protects the project: it shows competence without making a claim the sample cannot support.

## 5. Sequencing against the alternatives

| Path | Spend before first data | Risk |
|---|---:|---|
| Straight to ten | ~$2,100 | Camera, seal, or upload turns out wrong at scale; ten units wasted |
| Three, then ten | ~$700 + ~$1,400 | One extra phase; some duplicated setup |
| Three only | ~$700 | Cheap, but no study result at all |

The straight-to-ten path is only sensible if the bench measurements have already settled the camera question. They have not.

## 6. What it does for credibility

A town meeting and a pro bono lawyer will both respond better to *"we ran three units for ninety days, here is what happened, and here is what we propose next"* than to *"we would like to deploy ten cameras."*

A small trial is evidence. A proposal is a promise. In a town of 4,000, the difference is the whole argument.

## 7. Recommendation

**Run three units as a Phase 1b field trial, then decide on ten.**

Use the cellular build rather than the no-radio build, because the point is to test the real pipeline — upload, ingest, publication — not just the camera.

**Deploy all three on day one, each to a different household with its own volunteer.** Then run it rolling: when a module comes back — sealed, opened, stolen-and-returned, or failed — reset it and redeploy it at a **new** address as soon as it is ready, rather than waiting for a calendar boundary (D-70). Thirty days is the **maximum observation per placement and the point at which a survivor is censored**; it is not a wave that holds a working module in the workshop.

Turnaround budget: **three days** — inspection, record reconciliation, cell swap, fresh seal, wipe, rebox, host briefing. Faster is not credible; slower wastes exposure.

What rolling does and does not buy:

- **More placements, not more exposure.** Three modules in the field for ninety days is 270 module-days whether they are redeployed on recovery or on a fixed schedule. No cycling manufactures more instrument-time than the modules provide.
- **Placements are gated by recovery, and recovery is the event.** A module removed and never returned is gone and cannot be redeployed. At n=3, two unrecovered removals leave one module, and no schedule compensates. This is the strongest argument for ten modules over three, and for keeping the cellular build.
- **The sample grows fastest exactly when the pilot is going badly.** Because only disturbed-and-returned modules generate new placements, observation count tracks the removal rate. That is a property of the phenomenon rather than a defect, but it means rolling redeployment cannot be relied on to produce placements.
- **Recruitment becomes the rate-limiting step.** Every placement needs a new household (D-53), so fast cycling can exhaust the volunteer roster before day ninety. Budget the roster against placements, not against ninety days.
- **Calendar time is no longer balanced.** Rolling compresses later observations into later dates, and porch risk is seasonal. Record placement date and carry it as a covariate in the pre-registered analysis instead of assuming exchangeability across the trial.

The absolute floor, if recruitment or recovery stalls, is one placement per module for ninety days. Rolling is the recommendation because it costs $18 more in boxes and tests resets, handoffs, and cell swaps as a matter of course — the parts most likely to fail quietly.

## 8. What this does not change

The full pilot remains ten modules, 30 hosts, 90 days, and the primary outcome stays where D-47 put it. A three-unit trial is a gate, not a substitute — and no result from it should be pooled into the main analysis, because the hardware and procedures will have changed between the two.
