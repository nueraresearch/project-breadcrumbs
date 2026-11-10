# Town Meeting Briefing — Project Breadcrumbs

**Status:** Draft for the Monte Vista town meeting. Not yet presented. Plain-language briefing; no participant data.
**Version:** 0.3 (2026-11-10)
**Purpose:** To ask the town for support in principle for a 90-day voluntary pilot, and for its view on publishing images of the person who opens the box.
**Related:** [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md), [`PRE_REGISTRATION_ANALYSIS_PLAN.md`](PRE_REGISTRATION_ANALYSIS_PLAN.md), [`../governance/DATA_PROTECTION_CONTROLS.md`](../governance/DATA_PROTECTION_CONTROLS.md), [`../governance/PRIVACY_SAFETY_AND_REVIEW.md`](../governance/PRIVACY_SAFETY_AND_REVIEW.md), [`../review/REIDENTIFICATION_REVIEW.md`](../review/REIDENTIFICATION_REVIEW.md), [`PARTICIPANT_BRIEFING_AND_CONSENT.md`](PARTICIPANT_BRIEFING_AND_CONSENT.md), [`../../DECISION_LOG.md`](../../DECISION_LOG.md).

## 1. How to use this

- This is a 12 to 15 minute spoken briefing, followed by questions.
- The one-page handout in §4 can be copied for the table.
- The numbers in §2.3 are planning assumptions, not predictions. Say so.
- Do not give the collection point address, the recovery payment amount, or device details that would help someone recognise a box. Those are deliberately left out.
- If you do not know an answer, say so and offer to answer in writing. Do not improvise a figure.

## 2. The briefing

### 2.1 Why we are here

Thank you for having me. I am [name], and I am running a small research pilot called Project Breadcrumbs. I am here for two reasons: to explain what we want to do, and to ask for your view on the hardest part of it.

I want to be clear at the start. This is not a police operation. It is not a security product. It will not tell you how many packages are stolen in Monte Vista. It is a feasibility study: we want to find out whether a small, sealed research package can produce a reliable record of what happens to a package left on a porch.

We are asking the town for support in principle tonight. We have made town support a condition of fielding. If the town says no, we do not deploy.

### 2.2 What the pilot is

Ten sealed boxes. Thirty households. Ninety days. Each household keeps one box on its porch for thirty days, then returns it. Each box is used three times, at three different houses, so thirty households take part in total.

The box looks like an ordinary package. It is addressed to a study name that belongs to no real person. The household is told, in writing, not to open it. Inside is a small camera and sensors. The camera is blind while the lid is closed. If the box is opened, a light trigger takes up to three still pictures. There is no audio, no video, no continuous recording, and no facial recognition.

The box is not a camera on a porch. It is a camera inside a sealed box that only sees anything when the box is opened. That distinction matters, and I will come back to it.

### 2.3 What we can learn, and what we cannot

Here is the honest version. We can learn whether the hardware works in the field: whether it stays powered, captures images, records movement, and survives a thirty-day placement. We can describe what happened at thirty porches: how often a box was opened or moved, how long it took, how far a module travelled after it left the porch, and how often it came back. If enough removals happen, we can estimate a time-to-removal curve. If they do not, we will say the median is not estimable.

We cannot tell you the theft rate in Monte Vista. The households are volunteers, not a random sample. Thirty placements is a case series, not a survey. A percentage from this sample would look precise and be misleading.

We cannot tell you who opened a box. We do not identify people, we do not ask for names, and we do not publish identification requests.

We cannot tell you whether the box prevents theft. There is no comparison group of porches without a box. We are not testing the box as a deterrent; we are observing what happens at the porches that have one.

And we cannot promise that a removal is a theft. A neighbour may carry a box inside. A delivery person may move it. Someone may open it by mistake. The project treats a movement as a movement, not as proof of a crime.

Our planning assumption is small: across thirty placements of thirty days each, we expect somewhere between a quarter and a half of one removal. If that is right, there is roughly a one-in-four to two-in-five chance of seeing even one. Which means there is a three-in-five to four-in-five chance of seeing none.

People who have already lost a package may be more likely to volunteer, which could make the rate at these porches higher than the town rate. We have not changed the planning figure, because we cannot know how much higher. If it were twice as high, the chance of seeing at least one removal would be roughly two in five to three in five, not one in four to two in five. We will report the observed count against the exposure, not a town rate.

That is not a prediction. It is a planning number. And it leads to the most important thing I can say tonight: a run where every box stays sealed would be the best possible result for the households in it, and the least useful result for the main question. We would report zero events over the exposure, not a zero theft rate, and not proof that the box works. We would still report what the pilot was built to test: whether the hardware, the process, and the privacy controls worked.

If you take one thing away: this pilot is designed to produce an honest answer, including the answer "we could not measure it."

### 2.4 The hard part: publishing faces

Now the part I most want to talk about.

The project publishes its data. That is a deliberate choice. The public should be able to check the work, not take our word for it. The published data includes event records and, when the box is opened, images.

The current rule has limits. We do not publish a participant's name, address, or precise location. Location is a square about a kilometre across, published after a delay. Captions say a package was opened; they never say a theft occurred, and they carry no names or identification requests. Images of a minor, or a person with no connection to the opening, are never published; we publish the number withheld, by category.

But the adult who opens the box is published. Their face, and whatever is behind them.

Why would we do that? The argument is this. The package is addressed to a study name that belongs to no real person. The household is told not to open it. Anyone who opens it is opening mail that is not addressed to them. The image is the evidence of the event the study exists to observe. If we publish the event but not the image, we are asking the town to trust a claim we have chosen not to show.

The cost is just as real. The person in that photograph did not agree to be photographed. In a town of about 4,000, a face is not a data field; it is a name. Publication is permanent. A photograph can show more than a face: a door, a house number, a room, a screen, a photograph on a wall. We can withhold an image of a child or an uninvolved person, but we cannot promise that no identifying detail appears in a photograph of an adult who opened the box. And the person may be a neighbour, a young adult, or someone who made a mistake.

We are also honest that the data does not make a participant anonymous to their neighbours. We do not publish their name or address, but a neighbour who knows which porch had a box may be able to work it out. The one-kilometre cell is a neighbourhood, not a hiding place.

We have reviewed the published fields for what they can still reveal. The review found that a one-kilometre cell plus exact timestamps plus local knowledge can identify a porch, and that an image can show a house number or a room. Those are not solved. They are listed in the repository, and we are working on them.

So there is a genuine trade-off, and it does not have a comfortable answer. The current rule is to publish. The question I want to put to the town is whether that rule should be narrower for this pilot.

| Option | What the public sees | What it protects | What it costs |
|---|---|---|---|
| A. Publish as now | Event records and images; minors and uninvolved people withheld | The public can check the evidence; the project is transparent | The adult opener is identifiable to anyone who knows them; publication is permanent |
| B. Blur or crop faces | Event records and images with faces obscured | The opener is harder to identify | The public sees less; backgrounds may still identify; blur can fail; not implemented |
| C. Withhold images for the pilot | Event records and counts only | The opener is not published | The public cannot see the evidence; the image review still happens, but the dataset is thinner; a change to the current decision |

Option A is what we have now. It is the most transparent, and the hardest on the person in the photograph.

Option B would require a new review and editing step. It is not implemented. It reduces identification, but it may not remove it. A background, a jacket, or a street sign can still identify someone.

Option C protects the opener most, but the public sees less of the evidence, and it would be a change to the current decision.

I am not going to pretend the project has solved this. We are reviewing background checks, and the image rule may change before we field. But the decision belongs in public, not in a repository. That is why I am asking for your view.

### 2.5 Privacy and safety

The rest of the controls are less controversial, but they matter.

- The camera is inside the box and blind when the lid is closed. No audio, no video, no facial recognition, and no remote control. There is no way for the project to turn it on remotely.
- Images are encrypted at rest. Before release, they are seen only by named reviewers, and access is logged.
- We do not publish names, addresses, or precise coordinates. Location is a one-kilometre cell, delayed by about a month.
- We do not proactively give data to police. We comply with valid legal process after legal review, and we tell the participant unless the law bars us. Published data is already public. This position is part of the legal review.
- Participants can withdraw at any time, without a reason. The box is collected, future deployment stops, and they can ask for their records to be deleted. Anything already published cannot be recalled.
- We ask participants never to confront, follow, or identify anyone. If there is immediate danger, call the police, not the project.
- We do not ask anyone to retrieve a box from an unsafe place.
- The study does not pay for information, and it does not pay for a lost package. There is a small recovery payment only when a box that was taken from the porch is returned; a normal end-of-cycle return is not paid. The amount is not published, because a public offer could encourage someone to take a box in order to return it. The project does not decide whether a crime occurred; it uses its own record that the box left the porch.

### 2.6 What we are asking of the town

We are asking for three things.

First, support in principle for a ninety-day voluntary pilot, subject to the project completing its legal, ethics, and insurance reviews. This is not a request for town money. The pilot's cash budget is about $2,500, mostly hardware and recovery costs, with the work in-kind.

Second, your view on the image rule. If you think faces should not be published, say so. If you think the current rule is the right balance, say that too. We will record it and answer it in writing.

Third, if you are interested in hosting a box, or in reviewing the materials, talk to us after the meeting. We are not signing anyone up tonight, and no one is obligated by showing interest.

If the town does not support the pilot, we will not deploy. That is the gate.

### 2.7 What happens next

If the town supports the pilot, the next steps are legal and ethics review, recruitment of thirty households, and then the ninety-day pilot. We will publish the results, including what we could not conclude, and we will report back to the town.

If the pilot produces zero removals, we will say so. If the hardware fails, we will say so. If the privacy controls do not hold, we will stop.

Thank you. I am happy to take questions.

## 3. Questions we expect

**Is this surveillance?**
No continuous video, no audio, no facial recognition, and no remote control. The camera is inside a sealed box and blind until the box is opened. It captures up to three still images of the opening.

**Will you publish my face?**
If you are the adult who opens the box, the current rule publishes the image. If you are a minor or not connected to the opening, the image is withheld and deleted. We are asking the town whether the current rule should be narrower.

**What if a child opens it?**
The image is withheld, access-restricted, and deleted after the adjudication record is written. The number withheld is published by category. Age is estimated from appearance, and the rule errs toward withholding; some young adults will be withheld as a result. The event record still shows that an opening happened; we do not publish the image.

**Will you give data to the police?**
Not proactively. We comply with valid legal process after legal review, and we tell the participant unless the law bars us. Published data is public.

**Is there a recovery payment?**
Only when a box that was taken from the porch is returned. A normal end-of-cycle return is not paid. The amount is not published, because a public offer could encourage someone to take a box in order to return it.

**Will this reduce package theft?**
We do not know, and this pilot cannot answer that. There is no comparison group, and thirty volunteer households are not a town sample.

**Why not just ask people whether their packages were taken?**
Self-report is part of the picture, but it misses openings that are not reported and cannot measure time-to-removal. The pilot observes events at a small number of porches; it is not a town survey.

**Why thirty households for ten boxes?**
Each box is used three times, at three different houses, for thirty days each. One household hosts one deployment.

**What does it cost the town?**
No town funding. The project's cash budget is about $2,500, mostly hardware and recovery costs; the work is in-kind.

**Can I withdraw?**
Yes, at any time, without a reason. The box is collected, future deployment stops, and you can ask for your records to be deleted. Anything already published cannot be recalled.

**What if the town says no?**
We do not deploy.

**Who owns the data?**
The project owns it and publishes it. The town does not have to manage it.

**Why publish at all?**
So the public can check the work. A study that asks for trust without showing its evidence is asking for the wrong thing.

## 4. One-page handout

**Project Breadcrumbs — a 90-day voluntary pilot**

| Question | Answer |
|---|---|
| What is it? | Ten sealed boxes, thirty households, ninety days. Each household keeps one box for thirty days. |
| What does it record? | Up to three still images when the box is opened. No audio, no video, no facial recognition, no remote control. |
| What does it publish? | Event records and images. No names or addresses. Location is a one-kilometre cell, delayed. Minors and uninvolved people are withheld. |
| What can it tell us? | Whether the hardware works, what happened at thirty porches, how long a removal took, and how far a module travelled. |
| What can it not tell us? | The town theft rate, who opened a box, or whether the box prevents theft. |
| What is the face question? | The current rule publishes the adult who opens the box. The town's view is sought on whether to narrow that. |
| What are we asking? | Support in principle, your view on the image rule, and volunteers after the meeting. No town money. |

## 5. Where to read the detail

- [`PILOT_PROTOCOL_DRAFT.md`](PILOT_PROTOCOL_DRAFT.md)
- [`PRE_REGISTRATION_ANALYSIS_PLAN.md`](PRE_REGISTRATION_ANALYSIS_PLAN.md)
- [`../governance/DATA_PROTECTION_CONTROLS.md`](../governance/DATA_PROTECTION_CONTROLS.md)
- [`../governance/PRIVACY_SAFETY_AND_REVIEW.md`](../governance/PRIVACY_SAFETY_AND_REVIEW.md)
- [`../review/REIDENTIFICATION_REVIEW.md`](../review/REIDENTIFICATION_REVIEW.md)
- [`PARTICIPANT_BRIEFING_AND_CONSENT.md`](PARTICIPANT_BRIEFING_AND_CONSENT.md)
- [`../../DECISION_LOG.md`](../../DECISION_LOG.md)

## 6. Staff notes

- The planning figure is 0.25 to 0.5 expected removals across thirty porch-months; the chance of at least one is 22 to 39 percent, and the chance of none is 61 to 78 percent. These are assumptions, not measurements. The exposure is about 900 deployment-days. This is the unenriched base case. Risk-enriched recruitment is a 2× sensitivity: 0.5 to 1.0 expected removals, 39 to 63 percent chance of at least one, 37 to 61 percent chance of none. Do not present the sensitivity as the expected value.
- The current image rule is D-40 with the D-52 limits. Options A, B, and C are illustrations for the meeting, not approved changes. Do not say the project has decided to blur or withhold images.
- Do not state the recovery payment amount, the collection point address, or device construction details. The amount is kept out of public material (D-74), and device details are kept out to avoid helping someone recognise or defeat a box.
- The recovery payment is only for a box taken from the porch and returned. Do not describe it as payment for hosting or for a normal return.
- Town support is a condition of fielding (D-43). Legal, ethics, and insurance reviews are pending; this briefing is not a legal opinion.
- If the town advises a narrower image rule, record the advice and answer it in writing before any deployment.

## 7. Version history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-11-10 | First draft for the town meeting. No participant data. |
| 0.2 | 2026-11-10 | Added the risk-enrichment sensitivity to the planning assumption; base case unchanged. |
| 0.3 | 2026-11-10 | Limited the recovery payment to a box taken from the porch and returned; normal end-of-cycle returns are not paid (D-81). |
