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

## 9. The $1,000 cap (D-71) — superseded by §11

**Status:** Superseded, 2026-10-30. The cap was raised to $2,500 and the build to ten modules. Retained for the record and for the arithmetic behind the original three-plus-nine question.

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

*This split is superseded by §10. Once the run stops on a budget floor rather than a target sample size, holding a reserve matters more than the last two spares, and the build becomes seven modules with five fees and a $120 reserve.*

### 9.4 What nine spares would actually buy

With three modules fielded at a time, nine spares covers the loss of the entire fleet three times over. That is not over-insurance if the pilot is meant to keep running through losses — but each replacement needs a new household (D-53), so the constraint on using the ninth spare is recruitment, not money. Buying nine before the first deployment spends on a scenario the pilot may never reach.

Two of the assumptions above are provisional: the $40 fee (B-11, documented replacement cost, is still open) and the $60 shipping line, which was priced for repeat visits to a few addresses and will be higher across many host households.

## 10. Stopping rule: money or time, whichever comes first (D-72)

**Note:** the rule stands at any budget. The build table in §10.2 is priced at the $1,000 level and is superseded by §11.1.

**Status:** Owner constraint, 2026-10-30. Amends the module split in D-71; the $1,000 cap is unchanged.

### 10.1 The rule

There is no target sample size. Placements continue while both conditions hold:

1. money remains above the reserve floor, and
2. the 90-day window has not closed.

Whichever fails first ends recruitment of new placements. Modules already in the field are retrieved or censored.

### 10.2 Why the floor is not optional

A pure spend-down rule has a failure mode. The last dollars go out as a module goes out, and there is then nothing left to pay the fee that would bring it back. The pilot ends with an instrument in the field and no budget to recover it — the worst place to stop, because it turns a recoverable module into a loss and a censorable observation into a missing one.

So the rule needs a floor: **stop opening new placements when the remaining budget drops below one box, one fee, and one spare — about $114.**

That floor changes the build from D-71. Holding a $120 reserve costs two spares:

| Line | Amount |
|---|---:|
| Modules, 3 initial + 4 spares, at ~$72 | 504 |
| Extra boxes for redeployments | 10 |
| Shipping and insurance | 60 |
| Materials and ops kit | 40 |
| Hosting and tooling | 50 |
| Recovery fees, 5 at $40 | 200 |
| Reserve floor | 120 |
| **Total** | **984** |

### 10.3 What the stop does to the analysis

The stop is **administrative censoring**, and it has to be recorded as such: the date recruitment closed, and for every module still in the field at that instant, an observation censored there.

That is admissible, but only under two conditions.

- **The stop must be a rule, not a judgement.** "Budget fell below the floor on 12 January" is censorable. "We had seen enough" is not, and no analysis repairs it afterwards.
- **It must be recorded to the day.** A stop date reconstructed later from memory will silently truncate the highest-risk placements, because those are the ones that end earliest.

The harder point: **the stop is not independent of the outcome.** Money runs out faster when modules are lost and fees are paid, so the run ends sooner exactly when the removal rate is high. That would normally be informative censoring, which breaks survival estimates. It is tolerable here for one reason — the stop depends only on *observed* history: placements made, modules lost, fees paid. It never waits on an event that has not yet happened. A stopping time predictable from the observed past is admissible censoring; one that waits for a future event is not. The pre-registration plan should say so, and the analysis should report the stop date alongside the number of placements still open at that moment.

### 10.4 What the design produces instead of a sample size

With no fixed n, the useful outputs are the ones a spend-down plan generates naturally:

- **cost per completed placement** — the figure a funder actually asks for;
- **days per placement**, from deployment to reset;
- **placements achieved per module** over the window;
- **spend rate** in dollars per module-month, which is what prices a ten-module pilot.

At $984, nine placements works out at about $109 each; fifteen placements at about $66. Finding out which it is, is a real result rather than a placeholder for one.

### 10.5 The honest limitation

A run that stops when money runs out cannot promise a fixed number of events. If removals are rare, it ends with placements still open and no events at all — a clean feasibility result and no survival estimate. That is an acceptable outcome only if it is stated in advance, which this section does.

## 11. The $2,500 target (D-73)

**Status:** Owner direction, 2026-10-30. Supersedes the $1,000 cap in D-71 and the build in §10.2; the stopping rule in §10 stands.

### 11.1 Why ten modules rather than three

At $1,000, three modules was the right shape because the money barely covered the fixed costs. At $2,500 that reverses. **Module-months generate the observations, and they are the cheapest line in the budget** — $72 buys a module that produces thirty porch-days, about $2.40 per porch-day.

Three modules at this cap would leave most of $2,500 unspent on the only input that produces data.

| Line | Amount |
|---|---:|
| Ten modules at ~$72 | 720 |
| Boxes for thirty placements | 60 |
| Shipping and insurance | 200 |
| Materials and ops kit | 120 |
| Hosting and tooling | 150 |
| Reserve floor | 200 |
| **Committed** | **1,450** |
| Replacements, up to nine at $72 | 648 |
| Recovery payments, up to ten at $20 | 200 |
| **Contingent** | **848** |
| **Total committed and contingent** | **2,298** |
| Unspent against the $2,500 cap | 202 |

Committed spend is $1,450. The other $848 is spent only if modules are lost or boxes come back — the logic of §9.3 at ten times the scale.

The $202 left unspent is deliberate. Expected returns across thirty porch-months are 0.25 to 0.5, so ten recovery payments is already twenty to forty times the number likely to be paid; the money is far more likely to sit idle than to run out. Leaving it unallocated is cheaper than guessing which line will need it.

### 11.2 What $2,500 does not change

Thirty placements is still thirty porch-months, and expected removals are still **0.25 to 0.5**. The chance of observing at least one is **22–39%**. The chance of observing enough to draw a survival curve is negligible.

The honest description of this budget is **a properly run feasibility study**, not a measurement of theft.

If the goal is a rate rather than a study, $2,500 is year one of a multi-year programme. At the same base rate, about 1,000 porch-months are needed for roughly eight events: ten modules running continuously for eight years, recruiting 1,000 households in a town of 1,600. That is not a pilot, it is a standing survey, and it should be described as one before anyone funds the first year.

### 11.3 Where extra money should go

1. **Replacements** — protects the thirty-placement target through losses.
2. **A second wave of placements** — if recruitment holds and nothing is lost, the same money buys more porch-months, the only thing that improves the estimate.
3. **Recovery payments** — $20 each, contingent by nature, paid only on return.
4. **Nothing else.** Paid legal or ethics review belongs outside this figure. It is a programme cost, not a pilot cost, and folding it in distorts comparison with any future run.

### 11.4 The condition

The same one as before, and it gets sharper as the budget grows, because the temptation does too: **legal and ethics review must be $0.** A $2,000 ethics review would consume 80% of $2,500 and leave a five-hundred-dollar field programme. If either has to be paid, the honest move is to say the pilot costs $4,000–5,500 and fund it at that level, rather than squeeze the field work to protect a headline figure.

### 11.5 Labour and in-kind valuation (D-75)

The cash budget covers materials only. The project's own time is recorded here at a deliberately conservative rate, so the true cost is visible without inflating it.

| | |
|---|---:|
| Rate | $1,000 per month |
| Horizon | 6 months — firmware and build, recruitment, field phase, analysis |
| In-kind value | $6,000 |
| Estimated hours | 350–700 |
| **Implied hourly rate** | **$8.57–$17.14** |

Unpaid. Nothing in the $2,298 is a wage, and the pilot cannot pay one: three months at this rate alone would exceed the entire cash budget.

**Fully loaded cost:** $2,298 cash plus $6,000 in-kind is **$8,298**, or about **$277 per porch-month** across thirty placements. That is the figure to quote when someone asks whether the approach is cheap. The parts are cheap; the study is not.

**Why six months and not three.** Firmware is written before the first deployment, recruitment overlaps it, and analysis follows the last retrieval. Counting only the ninety field days would understate the work by roughly half.

**Why the rate is low.** Across 350–700 hours over six months the implied rate is $8.57–$17.14 an hour — at about the state minimum wage at the bottom of the range, and well below market for embedded work. That is a choice, not an error. An in-kind figure that looks generous invites scepticism; a conservative one is harder to argue with.

### 11.6 Full project cost, as a funder would price it

The $2,298 is the parts-and-operations bill and assumes legal and ethics review cost nothing. A funder will price them anyway, so a proposal should too.

| Scenario | Cash | In-kind | Total |
|---|---:|---:|---:|
| Reviews pro bono or waived | 2,298 | 6,000 | **8,298** |
| One review paid | 3,798–4,298 | 6,000 | **9,798–10,298** |
| Both reviews paid | 5,798 | 6,000 | **11,798** |
| Both paid at the top of their range | 7,298 | 6,000 | **13,298** |

Insurance is not priced in any row. It has to be quoted before submission, and it is the line most likely to appear late and quietly exceed the rest of the contingency.

**Recommended request: $5,000 cash against $6,000 in-kind, an $11,000 project.** That covers the pilot, one review at the top of its range, and a small buffer, and it is a round figure that can be approved without a second round of arithmetic. It sits comfortably inside the $1,000–$25,000 project band small rural foundations typically work in, which matters: an ask of $2,298 is liable to look like a rounding error rather than a project.

Two things to state plainly in the proposal, because a final report will have to state them anyway:

- **The deliverable is a feasibility finding, not a theft rate.** Thirty porch-months is a case series. If the proposal implies a town-wide measurement, the grant ends on a report that says the measurement was never possible.
- **The in-kind contribution is the larger half of the project.** $6,000 against a $5,000 request is roughly 55% of the total cost, which is a genuine leverage story rather than a formality.
