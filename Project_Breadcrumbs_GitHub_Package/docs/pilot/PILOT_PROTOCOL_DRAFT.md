# Project Breadcrumbs — 90-Day Pilot Protocol (Draft)

**Protocol version:** 0.2  
**Status:** Planning draft; not approved for field deployment  
**Sponsor/organization:** Nuera Research and Developmental Laboratories  
**Proposed setting:** Monte Vista, Colorado (D-43)

## 1. Purpose

Assess the feasibility of using reusable, event-monitoring packages to collect structured observations about package deployment, disturbance, opening-related sensor events, module movement, recovery, and reuse.

This is a feasibility and methods pilot. It is not designed or powered to estimate community-wide theft prevalence, identify offenders, establish guilt, or demonstrate that a particular intervention reduces crime.

## 2. Hypotheses

The primary feasibility hypothesis: a low-cost, reusable monitoring module can, after engineering validation, produce sufficiently reliable deployment and event records to support useful descriptive analysis of package-related events and recovery outcomes in a small voluntary pilot.

Several substantive hypotheses may be pre-registered alongside it in a dated file before fielding (D-49). They should concern what happens after a package leaves — how far it travels, how quickly it stops reporting, and how often it comes back — rather than how many packages are taken, which the sample cannot support.

## 3. Pilot targets

- **Duration:** 90 days.
- **Hardware:** 10 reusable modules.
- **Volunteer hosts:** 30, one deployment each (D-53).
- **Collection point:** the project's operating base in Monte Vista, by appointment (D-55). The address is held privately.
- **Cycle length:** 30 days per deployment cycle (D-34).
- **Cycles per module:** three, run back to back. The 90-day pilot is therefore three consecutive 30-day cycles per module, not one long deployment.
- **Total deployment cycles:** 30, being 10 modules × three cycles, each at a different host.
- **Preliminary budget target:** $600–$900, retained as a target rather than a budget (D-51).
- **Setting:** Monte Vista, Colorado, subject to town-meeting approval (D-43).

**Why 30-day cycles.** Each cycle boundary is a natural point to retrieve the module, swap the cell, offload stored records, and inspect the enclosure. It also bounds the period any single site is exposed, and it makes "one deployment" a unit that means the same thing for every module.

**Correction to earlier figures.** Previous concept documents cited approximately 120 deployment cycles. That figure was computed against 90-day cycles. At three 30-day cycles per module across 10 modules the total is 30. The 120 figure should not be used in planning; D-34 records the correction.

## 4. Study setting and participants

Proposed participants are homeowners in Monte Vista, Colorado who voluntarily agree to participate and place research packages on their own porches or other locations they control. Written authorization and clear participant instructions are required.

Monte Vista has a population of roughly 4,000, and volunteers collect and return their box at the project's operating base in town rather than at their own door (D-55).

The ten households are not a sample of Monte Vista and are not treated as one. They are **exposure**: thirty porches, thirty windows of thirty days, in which removal events can be observed. The object of study is the events — when they happen, what precedes them, and where a package goes afterwards — not a rate for the town. Reports describe events against exposure and do not present a percentage as if it estimated a town-wide theft rate.

Each household hosts one deployment and no more (D-53). Ten modules rotate through three hosts each, so the pilot needs **30 volunteer households**. That is a materially larger recruitment task than ten, and it is the main logistical risk in the design. The benefit is that every deployment is a distinct site, so the data no longer contain three repeated measures on the same porch.

Before recruitment or deployment, the project must complete legal, privacy, safety, insurance, and ethics review appropriate to the actual locations and methods. Town-meeting approval is the gate to fielding (D-43).

## 5. Study design

A small, repeated-deployment observational feasibility study with 30-day cycles.

Each cycle should record:
1. Module inspection and readiness.
2. Cell state and storage capacity check.
3. Participant-authorized placement.
4. Deployment timestamp and deployment record.
5. Monitoring period, including any movement events and location fixes.
6. Retrieval at the 30-day boundary, or earlier if the package is disturbed.
7. Cell swap and offload of all stored records.
8. Outcome classification and device inspection.
9. Reset and redeployment, if appropriate.

A cycle ends when the module is retrieved, its records are reconciled, and it is cleared for redeployment or retired. It then moves to a different host for the next cycle; it does not return to the same address (D-53). The protocol must define the check-in schedule, the recovery window, and the lost-device procedure before field use.

## 6. Data collected

Minimum proposed data:
- module identifier, deployment identifier, and a globally unique record identifier;
- deployment start/end timestamps;
- participant/site code rather than public participant identity;
- device health and battery status;
- event type and timestamp (light trigger, movement, communications, recovery);
- sensor-trigger confidence and diagnostic fields;
- location fixes with accuracy estimates and fix method;
- image references and capture timestamps;
- recovery status and recovery timestamp;
- outcome state, using the four categories in §7.4;
- maintenance and failure records.

**External context.** Delivery-volume data may be obtainable from the local post office for the routes serving the deployment area (D-56). It is sought as context, not as a sampling frame: the thirty deployments are not a random sample of deliveries, so the data cannot convert the results into a town theft rate. Any request should specify an aggregate scope — packages delivered over the study window for the relevant routes — and should be made under a written agreement. Recipient-level data is neither requested nor recorded. Where daily figures are available they are paired with removal dates, so an event day can be described alongside the number of packages the route carried that day — descriptive context, never a denominator. See the pre-registration plan, §7.1.

**Location is a primary output, not an optional extra (D-32).** Each movement event and each cycle boundary carries a location fix. This is how a removal is observed at all: the camera is inside the sealed box and sees nothing once the box is carried away.

**Publication of location is reduced in precision and delayed (D-41).** A precise coordinate identifies the volunteer's home rather than the subject. Operational records retain what is needed for analysis; published records do not contain a home address or a precise private-location trace.

## 7. Outcomes and metrics

### 7.1 Primary outcome (D-47, resolved)

**Primary: time from deployment to removal, analysed as a survival curve.** Each cycle contributes exposure from placement until it is removed or censored at retrieval, so the analysis uses all 30 cycles rather than only the ones that ended badly.

**Headline secondary: post-removal displacement** — how far and how quickly a package travels before it stops reporting.

**Descriptive: loss rate per 100 deployment-days.**

Removal, handling, and censoring are defined operationally, along with the adjudication rules, the exclusion rules, and the analysis itself, in [`PRE_REGISTRATION_ANALYSIS_PLAN.md`](PRE_REGISTRATION_ANALYSIS_PLAN.md). That document must be dated and committed before the first deployment.

### 7.2 Feasibility outcomes

- Successful deployment cycles / attempted cycles.
- Device uptime during scheduled monitoring.
- Event-record completeness.
- Movement-event registration rate, and location-fix success rate.
- Three-frame capture completion rate following qualifying triggers.
- False-trigger rate during controlled testing and field operation.
- Module recovery rate within the defined recovery window.
- Data synchronization success rate.

### 7.3 Secondary descriptive outcomes

- Time from movement event to recovery.
- Number of redeployment cycles per module.
- Maintenance interventions per cycle.
- Cost per completed deployment cycle.
- Participant feedback and burden.

### 7.4 Outcome states

Tracked separately, never collapsed into a single "loss" figure (D-50):

| State | Meaning |
|---|---|
| Not lost | Retrieved at the cycle boundary, intact |
| Recovered, redeployable | Returned and cleared for another cycle without repair |
| Recovered, refurbish | Returned but needing repair or parts before reuse |
| Lost, never recovered | Not returned within the recovery window |

### 7.5 Interpretation

A light trigger is not proof that a theft occurred, and an opening is not proof of intent. An image is not proof of identity. A recovered device's location does not by itself establish a disposal pattern; it establishes where the device was while it still had power. Results must include denominators, missing-data rates, and limitations.

## 8. Safety and incident response

- Volunteers must not confront, follow, detain, or attempt to identify anyone.
- Participants must be instructed to contact appropriate authorities if they believe an incident requires immediate assistance.
- Do not deploy in a way that creates a trip hazard, obstructs access, or encourages dangerous interaction.
- Establish a lost-device and data-breach response procedure.
- Suspend a deployment if the device behaves unexpectedly, creates a safety issue, or raises a privacy concern.
- The project does not solicit identification of any person depicted in published material, and will not host or relay such attempts.

## 9. Analysis plan and publication

Use descriptive statistics:
- counts and proportions by outcome state;
- event rates per deployment cycle and per 100 deployment-days;
- median and range for elapsed times where data permit;
- module-level reliability and recovery summaries;
- missingness and false-trigger analysis;
- qualitative summary of participant feedback.

Households are not a probability sample and are not treated as independent draws from the town. Report every event count against its exposure, in deployment-days, and report household-level counts only for completeness. Do not compute confidence intervals as if Monte Vista had been sampled; with thirty deployments and a handful of expected events, the honest output is a case series with known denominators.

**Publication.** Collected data, including images, is released publicly (D-40). Three limits apply and are not negotiable at the publication stage:

- No participant identity, home address, or precise private-location trace (D-41).
- Captions state that a package was opened, never that a theft occurred; no names, no identification requests, no guilt framing (D-42).
- Location precision and timing delays are applied before release, not removed on request afterwards.
- Images that appear to depict a minor, or a person with no connection to the opening, are never published; the number withheld is reported by category (D-52).

Avoid causal claims or generalisation beyond the small sample.

## 10. Pilot phases

### Phase 0 — Readiness (before day 1)
- Finalize hardware and software.
- Complete bench tests against the acceptance thresholds in the hardening plan.
- Complete legal/privacy/safety review.
- Finalize consent and participant materials.
- Finalize data retention and publication controls.
- Confirm budget and insurance.
- File pre-registration.

### Phase 1 — Prototype verification
- Test trigger, camera, movement logging, location, storage, power, and recovery workflow.
- Resolve critical defects before field use.

### Phase 2 — Participant onboarding
- Obtain written participation and property authorization.
- Explain the device, data collected, publication, risks, withdrawal, and incident procedure.
- Assign participant and deployment codes.

### Phase 3 — Field deployments (90 days, three 30-day cycles per module)
- Conduct scheduled, documented deployments.
- Retrieve and swap cells at each 30-day boundary.
- Monitor device health and participant concerns.
- Follow the approved recovery and data procedures.

### Phase 4 — Analysis and reporting
- Reconcile deployment and recovery records.
- Analyze reliability, recovery, data quality, and costs.
- Report limitations and recommendations.
- Publish released data according to §9.

## 11. Go/no-go criteria

Before field launch, establish numeric acceptance thresholds for:
- trigger false-positive rate;
- three-frame capture success;
- image quality;
- battery runtime across a 30-day cycle with margin;
- movement-event registration and location-fix success;
- data integrity;
- recovery workflow;
- privacy/security review completion.

Night opening detection is a declared scope limit rather than a threshold (D-30): it is measured and reported, not required to pass.

Do not begin field deployment while critical safety, privacy, legal, or data-security issues remain unresolved.
