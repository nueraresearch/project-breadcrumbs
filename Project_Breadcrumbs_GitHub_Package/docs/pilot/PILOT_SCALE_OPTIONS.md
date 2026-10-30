# Pilot Scale Options — 3, 6, or 10 Modules

**Status:** Analysis. No decision recorded; see open item D-04.
**Related:** D-53, D-65, [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md), [`../hardware/COST_REDUCTION_PLAN.md`](../hardware/COST_REDUCTION_PLAN.md)

## 1. The question

Ten modules is the planned pilot. Three is the smallest number that can prove the system works end to end. The gap between them is worth understanding before spending anything, because most of the cost is not per-module.

## 2. Cost at each scale

| | 3 modules | 6 modules | 10 modules |
|---|---:|---:|---:|
| Modules at ~$86 | 258 | 516 | 860 |
| Retail boxes, one per deployment | 18 | 36 | 60 |
| Connectivity, Hologram, 90 days | 19 | 37 | 63 |
| Legal review, pro bono target | 0 | 0 | 0 |
| Ethics review | 0–2,000 | 0–2,000 | 0–2,000 |
| Shipping and insurance | 100 | 200 | 400 |
| Materials and ops kit | 75 | 100 | 150 |
| Hosting and tooling | 100 | 150 | 200 |
| Contingency, 20% | ~115–460 | ~210–610 | ~350–750 |
| **Total, ethics waived** | **~$700** | **~$1,250** | **~$2,100** |
| **Total, ethics at $2,000** | **~$3,100** | **~$3,650** | **~$4,500** |

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

## 9. The $1,000 cap (D-71)

**Status:** Owner constraint, 2026-10-30. Hard ceiling for the three-module run.

### 9.1 The arithmetic problem

The requested configuration is three initial modules plus nine replacements — **twelve units in total**.

The ~$86 figure already carries a 30% spares allowance ($20 on top of $66 of parts), which is likely where the expectation of "spares built in" comes from. It buys about one spare for every three modules, not nine. Nine explicit spares is a different proposition: twelve units, at roughly $72 each including SIM and connectivity.

| Line | 3 + 9 (12) | 3 + 6 (9) | 3 + 5 (8) |
|---|---:|---:|---:|
| Modules, all-in at ~$72 | 864 | 648 | 576 |
| Extra boxes for redeployments | 10 | 10 | 10 |
| Shipping and insurance | 60 | 60 | 60 |
| Materials and ops kit | 40 | 40 | 40 |
| Hosting and tooling | 50 | 50 | 50 |
| Recovery fees, at $40 | 0 | 160 (4) | 240 (6) |
| **Total** | **1,024** | **968** | **976** |
| **Against the cap** | **−24** | **+32** | **+24** |

The requested configuration lands at about **$1,024 — over the cap, and with nothing left for a single recovery fee.** It does not fit, and no rounding makes it fit.

### 9.2 Conditions that make the cap possible at all

- **Legal review pro bono at $0.** A retained quote of $1,500–3,000 exceeds the cap by itself (D-54).
- **Ethics review waived or absorbed.** At $2,000 the run costs roughly three times the ceiling before a module is built. If ethics must be paid, this is not a $1,000 pilot and should not be described as one.
- **No paid labour.** Every hour is volunteer time.
- **Insurance is not in the budget.** General liability or volunteer coverage would either exceed the cap or has to come from the town or an existing policy. This is the line most likely to break the ceiling without anyone noticing, because it is normally purchased after the budget is written.

### 9.3 Whether a dollar should buy a spare or a fee

A spare module costs ~$72 and sits idle until something is lost. A recovery fee of $40 buys back a module worth ~$72, and produces a recovery observation as well as returning the instrument. Per dollar, the fee is the better purchase — while it works.

It only works when the box is opened by someone willing to return it, and reward-driven returns contaminate the recovery-time data the fees are meant to produce (M-03). The fee is a hedge, not a strategy.

**Recommendation: three initial modules, six spares, four recovery fees at $40 — nine modules, $968, with $32 held against the cap.** Three times cover on the three fielded units, and enough fees to learn whether returns happen at all. Four is not a large number; it is enough to distinguish "returns do not happen here" from "returns happen sometimes".

### 9.4 What nine spares would actually buy

With three modules fielded at a time, nine spares covers the loss of the entire fleet three times over. That is not over-insurance if the pilot is meant to keep running through losses — but each replacement needs a new household (D-53), so the constraint on using the ninth spare is recruitment, not money. Buying nine before the first deployment spends on a scenario the pilot may never reach.

Two of the assumptions above are provisional: the $40 fee (B-11, documented replacement cost, is still open) and the $60 shipping line, which was priced for repeat visits to a few addresses and will be higher across many host households.
