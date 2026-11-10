# Expected Removals and Risk-Enriched Recruitment

**Status:** Decision note supporting D-80. Planning analysis, not a measurement.
**Version:** 1.0 (2026-11-10)
**Decision:** The base case of 0.25–0.5 expected removals across thirty porch-months does not move. A 2× risk-enrichment sensitivity (0.5–1.0) is recorded as a planning stress case, not a revision.
**Related:** D-47, D-48, D-73, D-80; [`PILOT_SCALE_OPTIONS.md`](PILOT_SCALE_OPTIONS.md) §11.2; [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md) §4.2 and §9; [`PRE_REGISTRATION_ANALYSIS_PLAN.md`](PRE_REGISTRATION_ANALYSIS_PLAN.md) §8; [`TOWN_MEETING_BRIEFING.md`](TOWN_MEETING_BRIEFING.md).

## 1. What the figure is

The pilot plans around **0.25–0.5 expected removals across thirty porch-months**, which is thirty placements of thirty days each, or about 900 deployment-days. The figure is used to set expectations for the chance of observing at least one removal, to size the recovery-payment line, and to describe what a zero-removal run would mean. It predates this note and is not derived from a local measurement.

It is not a town theft rate, not a measurement, and not an input to the analysis. The analysis reports observed events against exposure, as §7 and §8 of the pre-registration plan require.

At 0.25 and 0.5 expected events, a Poisson process gives a 22–39% chance of at least one removal and a 61–78% chance of none. Those are the figures already used in the protocol and the town briefing.

## 2. Why risk-enriched recruitment matters

Recruitment is voluntary and open. The project does not select households on the basis of prior victimisation (protocol §4.2). But a household that has already had a package taken has a reason to volunteer that an untouched household does not, so the thirty porches will probably over-represent households with a prior removal. Prior victimisation is a plausible marker of higher risk, which would raise the expected number of removals relative to an unselected sample.

The direction is plausible, not certain. A prior victim may have become more careful, may have moved, or may have volunteered because of a one-off event that is not repeating during the thirty-day window. The sample is also small and geographically clustered. The net effect on the hazard during the pilot could be higher, lower, or the same.

The magnitude is unquantified. There is no local prior-victimisation rate in the project, no measured repeat-victimisation factor for these porches, and no pilot data yet. The protocol already says prior victimisation is "a plausible source of enrichment, not a planning figure" (§4.2), and the pre-registration plan says it is "reported as a limitation and is not used to adjust any estimate" (§8).

## 3. Whether the figure should move

**The base case does not move.** Replacing 0.25–0.5 with a higher point estimate would be inventing a magnitude the project does not have. It would also blur the distinction between a planning assumption and an analysis estimate, which the pre-registration plan deliberately keeps separate.

**A sensitivity is added.** The note records a 2× enrichment case, 0.5–1.0 expected removals, as the planning stress case. It is not the expected value and it does not replace the base case. The 2× factor is an assumption chosen to show what a doubling would do; it is not a measurement. A 3× case is also shown as an upper sensitivity.

## 4. Sensitivity table

| Enrichment | Expected removals | Chance of at least one | Chance of none |
|---|---:|---:|---:|
| 1.0× (base) | 0.25–0.5 | 22–39% | 61–78% |
| 1.5× | 0.375–0.75 | 31–53% | 47–69% |
| 2.0× (stress) | 0.5–1.0 | 39–63% | 37–61% |
| 3.0× (upper) | 0.75–1.5 | 53–78% | 22–47% |

Notes:

- Poisson approximation, the same basis as the existing 22–39% figure. These are planning ranges, not confidence intervals.
- The 2× case is the stress case for planning. The 3× case shows how quickly the chance of observing an event rises if enrichment is stronger; it is not a prediction.
- The table is about the chance of seeing at least one event, not about the precision of a rate. Even at 3×, thirty placements do not estimate a town rate.

## 5. What this changes

- **Decision log:** D-80 records the base case and the sensitivity.
- **Protocol §9:** states the base case and the 2× sensitivity together.
- **Protocol §4.2:** says the base case is not adjusted; the sensitivity is recorded separately.
- **Scale options §11.2:** keeps 0.25–0.5 and adds the 2× range.
- **Pre-registration §8:** keeps the limitation and adds the planning-only sensitivity; the analysis is unchanged.
- **Town briefing:** gives the base case and the 2× range in plain language.
- **Budget:** no change. Ten recovery payments are budgeted; at 2× expected returns are 0.5–1.0, so the line still covers well over the expected number. At 3× it covers 0.75–1.5.

## 6. What this does not change

- It does not change D-73's budget or D-47's primary outcome.
- It does not create a control arm or support a causal claim about the device (D-48).
- It does not adjust the analysis for enrichment after the fact.
- It does not turn the pilot into a rate estimate.
- It does not make the 2× factor a measured quantity.

## 7. What would change the decision

The figure should be revisited if any of the following arrives before fielding:

- a local prior-victimisation rate with a documented source;
- a measured repeat-victimisation factor for the recruitment area;
- a pilot run or Phase 1b field trial that produces an observed removal rate;
- a pre-specified enrichment factor from a credible local source that the owner adopts before deployment.

A revision should record the source, the factor, the date, and whether it was chosen before or after seeing data. A revision after seeing data is a deviation, not a planning assumption.

## 8. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-11-10 | Recorded the base case and the 2× risk-enrichment sensitivity (D-80). |
