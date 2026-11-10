# Privacy, Safety, Legal Review, and Data Governance

**Status:** Required pre-deployment work; not legal advice

## 1. Purpose

Project Breadcrumbs proposes voluntary porch deployments of packages containing event-monitoring modules. The camera is mounted inside the sealed package, aimed at the opening, and occluded by the lid until the package is opened (D-27). It captures three still images after a light-sensitive trigger (D-09). Its field of view therefore exists only while the box is open, which excludes the street, neighbours, and passers-by, but it will capture the face and upper body of whoever opens the package. Those images are published (D-40), subject to the limits in §3.

The package is addressed to a screened study name that belongs to no one with a connection to the address or the project, and the host is instructed in writing not to open it (D-77, D-78). The person the camera captures is therefore not a recipient opening their own mail; they are opening a package addressed to someone else. That is the factual premise for the position recorded in D-42. It is not a claim that the person has no privacy interest: the limits in §3 still apply, and an image of anyone who appears unconnected to the opening is never published.

The project must address these risks before field deployment.

## 2. Authorization

- Obtain written authorization from the participating property owner or other person with authority over the deployment location.
- Define the precise deployment area and permitted activity.
- Do not deploy on another person's property without authorization.
- Participant authorization does not automatically resolve legal restrictions relating to photographing or recording other people.
- Obtain jurisdiction-specific legal review for each deployment model and relevant state/local law.

## 3. Imaging constraints

Proposed system constraints:
- Still images only.
- Three images per qualifying trigger.
- No audio.
- No continuous video.
- No facial recognition or biometric identification.
- No automated person identification.
- Camera field of view physically limited to the package-opening area by fixed mounting and a fixed-focus lens.
- Collected images are published (D-40). Captions state that a package was opened rather than that a theft occurred, and carry no names, identification requests, or guilt framing (D-42).
- No exterior notice is used; the package is presented as an ordinary shipment (D-39).
- The package is addressed to a screened study name belonging to no one connected to the address or the project, with a written no-open instruction to the host and the host's confirmation that the name is not in use at the address (D-77, D-78).
- No published field identifies the participant or the volunteer's property: no name, no address, no precise coordinate (D-41).
- Images that appear to depict a minor, or someone with no connection to the opening, are never published. They are flagged at adjudication, access-restricted, and deleted once the adjudication record is written (D-52). The number withheld is published by category.
- Image reviewers recuse themselves if they know the participant, the household, or the deployment address, or if they recognize anyone in a frame (D-79). A reviewer who recognizes someone after viewing stops and records no decision; the record goes to another reviewer.
- A frame that appears to contain a bystander is reviewed by two reviewers, each of whom has opened every frame. If either withholds, the decisions differ, or no second reviewer is available, the image is withheld (D-79).

Whether participant notice or additional disclosure is required or appropriate must be determined through legal review and documented project policy. Do not assume property ownership alone resolves all privacy or recording issues.

## 4. Participant information

Before participation, explain:
- the research purpose;
- the camera orientation and trigger behavior;
- the addressing rule, how the study name is checked with the host, and that the box must not be opened by the host or the household (D-77, D-78);
- the types of data collected;
- possible incidental capture of people;
- who can access data before release, including the recusal rule and the second reviewer required when a bystander appears in a frame (D-79);
- what is published, and that publication is permanent;
- how to request suspension or withdrawal;
- what happens to data already collected;
- safety instructions and contact details;
- that the project is not a law-enforcement response service and does not encourage confrontation.

The draft materials are in [`../pilot/PARTICIPANT_BRIEFING_AND_CONSENT.md`](../pilot/PARTICIPANT_BRIEFING_AND_CONSENT.md).

## 5. Data minimization and security

- Collect only fields needed for the approved research questions.
- Keep participant contact details separate from device/event data.
- Encrypt stored images and transmitted data.
- Restrict image access to named personnel with a defined need.
- Log image access and exports.
- Use strong device identity and access controls.
- Define secure backup, deletion, and breach-response procedures.
- Do not put private addresses, raw images, credentials, or secret keys in this GitHub repository.
- Report event data at the level published under D-40, while suppressing anything that identifies a participant or a volunteer's property (D-41).

## 6. Retention

A specific retention schedule must be approved before field deployment. Published material is a separate category: once released it cannot be retrieved, so the retention schedule governs working copies rather than the publication. The schedule should define:
- routine image retention;
- event metadata retention;
- participant/contact record retention;
- incident-related preservation exceptions, if legally required;
- deletion verification and audit records.

Do not leave image retention indefinite by default.

## 7. Safety and conduct

- Volunteers must not confront, follow, detain, threaten, or attempt to identify anyone.
- Do not create physical hazards or obstruct public access.
- Do not encourage participants to retrieve a package/device from an unsafe location.
- Any suspected crime or immediate danger should be handled through appropriate official channels.
- Establish a process to pause or terminate a deployment if a safety or privacy concern arises.

## 8. Legal and organizational review checklist

Before field use, obtain qualified review of:
- state and local laws governing photography, surveillance, privacy, and recording;
- any applicable consent or notice requirements;
- property and trespass issues;
- data protection and breach notification obligations;
- reward/incentive program terms;
- postal rules and consumer-protection law bearing on a parcel addressed to a fictitious addressee;
- insurance and liability;
- whether institutional or independent research ethics review is appropriate;
- any rules governing sharing information with law enforcement or third parties.

**Pro bono counsel (D-54).** The project targets a local lawyer willing to do this review without charge, and budgets for it at zero. That is a reasonable target for a small community study, but two things must not follow from it. Free does not mean reduced scope: every item above still needs an answer in writing. And a general practitioner may not cover surveillance, privacy, and recording law in depth, so the scope is to be confirmed before work starts, and a gap is to be treated as a gap rather than assumed away.

This document is a planning checklist, not a legal opinion or assurance that a proposed deployment is lawful.

## 9. Incident response

Document procedures for:
- accidental or excessive image capture;
- unauthorized access or data disclosure;
- lost or stolen module;
- participant complaint or withdrawal;
- device malfunction;
- unsafe recovery situation;
- request from an authority or third party for data.

Assign an accountable project lead before field deployment.
