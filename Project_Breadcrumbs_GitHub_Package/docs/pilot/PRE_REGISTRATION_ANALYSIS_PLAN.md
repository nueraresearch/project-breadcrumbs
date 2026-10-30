# Pre-Registration — Analysis Plan

**Version:** 1.0-draft  
**Status:** Draft for filing. Must be dated and committed before the first Phase 3 deployment.  
**Related:** D-47, D-49, [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md) §7, [`../design/HARDENING_PLAN.md`](../design/HARDENING_PLAN.md) §6

## 1. Why this document exists

Pre-registration fixes the primary outcome, the analysis, and the exclusion rules **before** any data exists.

With 30 cycles, every analytic choice is an opportunity to find a pattern that is not there. Choose the outcome after seeing the data and the result is unfalsifiable; choose the subgroup after seeing the data and it will always look interesting. Writing the choices down first is the cheapest available defence, and it costs an afternoon.

Once filed, this document is amended only by dated amendment. Silent edits are not permitted.

## 2. Decision: the primary outcome (D-47, resolved)

**Primary outcome: time from deployment to removal, analysed as a survival curve.**

Every cycle contributes exposure from the day it is placed until it is removed or censored at retrieval. That is the decisive advantage over a proportion: a proportion needs a denominator this sample cannot supply, while a survival analysis uses all 30 cycles, including the ones that ended well.

**Headline secondary: post-removal displacement** — how far, and how quickly, a package travels after removal before it stops reporting. This is what the location telemetry exists to produce, and it is not well covered in existing work.

**Descriptive: loss rate per 100 deployment-days**, which normalises for unequal exposure between cycles.

### Why not the other two as primary

| Candidate | Why it is not primary |
|---|---|
| Loss rate per 100 deployment-days | With 30 cycles the denominator is tiny, and self-selected households are not independent draws. A percentage would carry false precision |
| Post-removal displacement | Conditional on a removal having occurred. If removals are few, there is little to describe, and the study would have no primary measure on cycles that were not removed |

Displacement remains the most novel measure in the study. It is secondary because it depends on an event that may be rare, not because it is less interesting.

## 3. Definitions

Fixed here so they cannot drift once data arrives.

| Term | Definition |
|---|---|
| **Deployment** | A module placed at an authorised site with an open deployment record |
| **Deployment point** | The location fix taken at placement, or the median of the placement fixes if more than one |
| **Movement event** | An accelerometer threshold crossing recorded by the device |
| **Removal** | The first movement event after which the module either never reports again, or reports a location outside the removal radius of the deployment point |
| **Handling (not removal)** | A movement event followed by a return to within the handling radius within the handling window |
| **Censored** | Retrieved at the cycle boundary without removal; withdrawn by the participant; or lost to device failure before any removal |
| **Exposure** | Days from placement to removal or censoring |
| **Displacement** | Distance from the deployment point to the last location fix, and elapsed time from removal to that fix |

**Proposed parameter values**, to be confirmed against measured fix accuracy at filing and then frozen:

- removal radius: 50 m
- handling radius: 10 m
- handling window: 30 minutes

If measured GNSS accuracy indoors or under a porch roof cannot support a 50 m radius, the radius moves and the change is recorded as a pre-filing amendment with its reason. It does not move after data collection begins.

## 4. Hypotheses

- **H1 (primary):** the time-to-removal distribution is estimable, with a median and interquartile range, and the study can report how many cycles remained at risk at each interval.
- **H2 (secondary):** post-removal displacement is estimable for removed modules, reported as median, interquartile range, and range.
- **H3 (descriptive):** removal rate per 100 deployment-days, with an exact interval, labelled descriptive.
- **H4 (exploratory, clearly labelled):** time-of-day and day-of-week patterns in removal events.

No hypothesis concerns *who* removed a package. The study cannot estimate that, and §7 forbids the analysis that would pretend to.

## 5. Inclusion and exclusion

Include every deployment with a valid deployment record and at least one location fix at placement.

Each deployment comes from a distinct host household (D-53), so a household contributes one observation. The unit of observation is the deployment; the object of study is the removal event. Households supply exposure and a denominator, not a sample of the town.

Exclude from analysis, with the reason recorded:

- deployments where the module failed before the first location fix (device failure, not an outcome);
- deployments withdrawn by the participant (censored at withdrawal).

**Never exclude a module that was not recovered.** Non-recovery is the outcome, not missing data. Any table whose denominator silently drops the lost cases is wrong, and this rule exists because that error is easy to make and hard to see.

## 6. Event adjudication

Two reviewers independently classify each movement-event sequence as **removal**, **handling**, or **indeterminate**, using only the event log and location fixes. Disagreements go to a third reviewer, and the rule applied is recorded.

Indeterminate is a retained category, reported as its own row. It is not dropped and not forced into one of the other two.

Reviewers do not see images while adjudicating. The classification must rest on telemetry alone, so that it remains available for modules whose images were never recovered — which is precisely the interesting case.

## 7. Analysis

**Primary.** Kaplan–Meier curve of time to removal, with a 95% confidence band, a number-at-risk table, and the number of events. If fewer than five removal events occur, the median is reported as **not estimable** rather than computed from a handful of points. That is a finding about the sample, not a failure of the analysis.

**Secondary.** Displacement: median, interquartile range, range; a scatter of distance against time-since-removal. No inferential test. With a handful of removed modules a test would manufacture significance from noise.

**Descriptive.** Removal rate per 100 deployment-days with an exact (Poisson) interval, explicitly labelled descriptive.

**What will not be done**, stated in advance so that its absence is not later read as an oversight:

- no multivariable modelling — 30 households cannot support it;
- no subgroup analysis;
- no causal claim about the device, the neighbourhood, or any intervention;
- no per-cycle confidence intervals presented as if cycles were independent observations;
- no imputation of missing locations.

Event counts are reported against exposure in deployment-days. Household-level counts are reported for completeness and to show where the events fell, not as an estimate of a town rate. Thirty deployments is a case series with known denominators; it is not a survey.

### 7.1 Contextual exposure: same-day delivery volume (D-56)

For every day in the study window, record two numbers: the number of packages the relevant postal routes carried that day (aggregate, supplied under written agreement), and the number of removals recorded that day.

The purpose is context, and it is useful context. A removal on a day when the route carried twenty-two packages is a different observation from the same removal on a day when it carried four. Volume varies by weekday, by season, and sharply through November and December, so a bare date tells you less than a date paired with how many packages were actually on porches that day.

The pairing is descriptive and reported as such: "removals occurred on a day on which the route carried N packages in total." It is not a denominator, and no rate is computed from it, because the study's households were not drawn from those deliveries and their packages are exposed for far longer. That sentence is written here once so the arithmetic is not run later and presented as a rate.

If daily figures are unavailable, weekly aggregates are acceptable and the comparison is correspondingly coarser. Pairing is by date and route or area only; no recipient-level data is requested, held, or recorded.

## 8. What this sample can and cannot conclude

Thirty deployments yield thirty exposure windows of thirty days each, so the study can describe removal events against roughly 900 deployment-days. What it cannot do is estimate a theft rate for Monte Vista: the households were not randomly selected, and the post office comparison (D-56), if obtained, supplies delivery volume rather than a sampling frame.

As an illustration of precision rather than a prediction: a 10% proportion observed in 30 cycles carries a 95% interval of roughly 3% to 25%. That width is the reason the primary outcome is a time-to-event measure rather than a proportion.

## 9. Deviations

Every deviation is logged with four fields: what changed, why, the date, and whether it occurred before or after the analyst had seen the relevant data. A deviation recorded after seeing the data is disclosed as such; it is not disqualifying, but concealing it is.

## 10. Publication mapping

Analysis outputs are published under D-40, with the limits already fixed elsewhere:

- no participant identity, home address, or precise location trace (D-41);
- captions state that a package was opened, never that a theft occurred; no naming, no identification requests (D-42);
- site-level cells below n = 5 suppressed;
- images that appear to depict a minor or an unconnected person are never published, and are deleted once the adjudication record is written (D-52).

## 11. Reproducibility

- Analysis code versioned in the repository, with the version recorded in the report.
- A single documented path from raw records to derived tables, with no manual spreadsheet steps in between.
- Before publication, a second person re-runs the primary analysis from the raw data and confirms the reported numbers. The confirmation is recorded with a name and a date.

## 12. Freeze checklist

- [ ] Primary outcome fixed (D-47)
- [ ] Removal radius, handling radius, and handling window fixed against measured accuracy
- [ ] Adjudication procedure and reviewers named
- [ ] Exclusion rules fixed
- [ ] Analysis code written and run against synthetic data
- [ ] Deviations log opened
- [ ] Document dated and committed before the first deployment
