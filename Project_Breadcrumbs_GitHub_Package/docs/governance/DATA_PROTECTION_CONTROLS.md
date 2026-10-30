# Data Protection Controls — Project Breadcrumbs

**Status:** Proposed defaults. These are conservative values chosen so that a future decision can only tighten them. They are not legal advice and must be reviewed by counsel before field use.
**Companion documents:** [`THREAT_MODEL.md`](THREAT_MODEL.md), [`PRIVACY_SAFETY_AND_REVIEW.md`](PRIVACY_SAFETY_AND_REVIEW.md), [`../data/DATA_MODEL.md`](../data/DATA_MODEL.md)

## 1. Why defaults rather than blanks

`PRIVACY_SAFETY_AND_REVIEW.md` §6 requires that a retention schedule be approved before deployment, and §5 requires access restriction and breach procedures. Those requirements are correct and, as written, unimplementable: there is no schedule to approve and no procedure to follow.

An unset control does not stay unset. It gets set by whoever builds the first pipeline, under time pressure, with whatever is convenient. The purpose of this document is to make the safe choice the default choice, and to make any departure from it a recorded decision with a name attached.

## 2. Roles

| Role | Responsibility | May not |
|---|---|---|
| Study Lead | Accountable controller; approves deployments, access grants, and any departure from this document | Be the sole reviewer of images |
| Image Reviewer | Named individual authorised to view captured images for adjudication | Export, screenshot, or discuss image content outside the review record |
| Analyst | Works with event metadata and de-identified extracts | Access images or contact data |
| Safety Contact | Receives participant concerns; can pause a deployment | Access the dataset |
| Technical Operator | Deploys, retrieves, extracts, resets modules | View images beyond the extraction verification step |

The separation that matters is Analyst ↔ Image Reviewer. In a five-person project they will sometimes be the same person; when they are, it is recorded, and the two-person rule for image access (below) still applies.

## 3. Access control matrix

| Data class | Study Lead | Image Reviewer | Analyst | Safety Contact | Technical Operator |
|---|---|---|---|---|---|
| Participant contact details | R/W | — | — | R | — |
| Consent records | R/W | — | — | R | — |
| Participant ↔ code mapping | R/W | — | — | — | — |
| Event metadata | R | R | R | — | R (own deployments) |
| Recovery records | R/W | R | R | — | R/W |
| Raw images | R (2-person rule) | R (2-person rule) | — | — | — |
| Image derivatives | R/W | R | — | — | — |
| Aggregate dataset | R/W | — | R/W | — | — |
| Audit logs | R | — | — | — | — |
| Device keys | R | — | — | — | — |

**Two-person rule:** raw images are viewed only with a second authorised person present or asynchronously logged, both names recorded. This is not a check on competence; it is a check on curiosity. It also means an accidental disclosure is witnessed and reportable rather than silent.

**Access hygiene:** named accounts only, no shared logins, MFA required, no personal cloud storage, no dataset on personal devices, no image transfer by messaging application. Every grant has an expiry date and is reviewed quarterly.

## 4. Encryption and key management

The current documents require "local encrypted image storage" and "encrypted transmission" without specifying an architecture. An unspecified encryption requirement is usually satisfied by a password on a folder, which protects against almost nothing relevant here.

**Recommended architecture (Tier B from the threat model):**

| Layer | Control |
|---|---|
| Device storage | Per-device X25519 keypair. Images encrypted with an ephemeral symmetric key, wrapped to the **study public key** using a sealed-box construction (X25519 + ChaCha20-Poly1305 or equivalent). The device holds only the public key, so a stolen device yields ciphertext and cannot decrypt its own archive. |
| Device keys | Study private key held offline, passphrase-protected, in two custodial shares. No copy on any internet-connected machine. |
| Extraction | Images arrive over the cellular link (D-33) and are written to the vault by the ingest service, logged with module ID, deployment ID, timestamp, and receiving operator. Physical recovery is used for reconciliation and for records buffered while the device was offline. |
| Image vault | Encrypted at rest, access-logged, no bulk export path. |
| Analysis environment | Contains de-identified extracts only. |
| Transport (metadata) | TLS with pinned server identity; device authenticates with a provisioned credential, never a shared secret across units. |
| Firmware | Signed images; secure boot enabled; debug interface disabled on production units. |

**Crypto-shred:** retirement of a module, or withdrawal of a participant, is implemented by destroying the wrapped key material for the affected records. This makes deletion verifiable without relying on physical media destruction, and it means a later discovery of an old backup does not resurrect deleted images.

**What not to do:** device-side passwords, a single fleet-wide key, storing the study private key on the same machine as the vault, or "encryption" implemented as a file permission.

## 5. Retention schedule (defaults)

These are the defaults. They exist so that absence of a decision does not become indefinite retention.

| Data class | Default retention | Then | Verification |
|---|---|---|---|
| Published release (images, events) | Permanent; this is the research output (D-40) | — | Not applicable. Publication is irreversible, which is why D-41 and D-42 are applied before release |
| Raw images, working copies after publication | 90 days after acceptance of the final pilot report, or 12 months after capture, whichever is sooner | Destroy wrapped keys; delete objects | Deletion manifest with object hashes and key-destruction record |
| Raw images, event unresolved or under complaint | Until resolution + 90 days | As above | As above |
| Raw images on device, never retrieved within the deployment window | Auto-delete on device at 30 days after capture, or on reset, whichever is first | Overwrite | Firmware log entry per deletion |
| Event metadata | 24 months after study close | Aggregate only | Row-count reconciliation |
| Recovery and reward records | 24 months after study close | Aggregate only | As above |
| Participant contact details | 12 months after withdrawal or study close, whichever is sooner | Destroy | Deletion record, named operator |
| Consent records | 36 months after study close (defensibility) | Destroy | As above |
| Participant ↔ code mapping | Destroyed at study close, after final reconciliation | Destroy | Lead witness record |
| Audit logs | 24 months | Destroy | As above |
| Published aggregates | Indefinite | — | Suppression rules in §8 |

**Out of scope for retention:** nothing. If a data class is not in this table, it should not be collected. Adding a class requires adding a row here first.

**Exceptions:** legal hold, a specific lawful preservation obligation, or an active complaint suspends deletion for the affected records only, and the suspension is logged with its reason and its reviewer. A hold with no expiry date is not permitted.

## 6. Deletion verification

A retention policy that is not verified is a policy about intentions. For each scheduled deletion:

1. Generate a manifest of affected object identifiers and content hashes before deletion.
2. Destroy the wrapping keys.
3. Delete the objects.
4. Attempt retrieval of a random sample and record that it fails.
5. Store the manifest, the sample result, and the operator name in the audit record.

Deletion is complete when step 4 succeeds and step 5 is filed. Not before.

## 7. Law enforcement and third-party requests

This is a recorded decision, not an operational habit. The project must choose one position and state it in the consent materials.

Published material is already public (D-40). The controls below govern participant identity, contact records, and the working dataset.

**Proposed default: research-only, compelled-process-only.**

- The project does not proactively provide images, event records, or participant information to law enforcement.
- The project complies with valid legal process, after review by counsel, and after attempting to narrow the request.
- Participants are notified of any request before disclosure unless legally barred, and are told if a bar applies.
- No informal requests are honoured, including "just a look" or "can you confirm whether anything happened at this address".
- Every request, response, and notification decision is logged.
- Anything not collected cannot be demanded. This is the strongest available protection and it is the reason data minimisation is a security control rather than a courtesy.

The alternative position — cooperating proactively with police — is legitimate for some projects but changes the ethics review, the consent text, the insurance position, and the participant risk profile. It must not be adopted by drift.

**Why this matters concretely:** if images reach a prosecutor, a participant's household becomes a witness in a criminal matter, may be subpoenaed, and may become known in the neighbourhood as the household that reported. None of that is within the project's control once disclosure occurs.

## 8. Publication controls

Applied in code, not by reviewer discipline. With 30 cycles in total, most cross-tabulations will fall below the suppression floor. That is expected, and it is why D-40 publishes event-level records rather than a table of rates.

- No published cell with **n < 5**. Suppress, do not blur.
- No cross-tabulation using `site_code`, directly or by combination.
- Timestamps published as coarse bins (week, or multi-hour band), never exact.
- No per-site sequences that allow ordering a single household's events.
- Images are published (D-40). Captions state that a package was opened, never that a theft occurred; no names, no identification requests, no bounty framing (D-42).
- No published field identifies the participant or the volunteer's property: no name, no address, no precise coordinate (D-41). Location is coarsened and delayed before release.
- Recovery time reported as median and interquartile range, never as a full per-device series.
- Differences under the pilot's detection floor are described as "not distinguishable from no difference", not as trends.

A small pilot's most likely public failure mode is not a data breach — it is a bar chart that lets a neighbourhood work out which house is which.

## 9. Breach and incident response

| Phase | Required action | Deadline |
|---|---|---|
| Detection | Any staff member who suspects a breach reports it to the Study Lead, without first investigating | Same day |
| Containment | Revoke access, rotate affected credentials, isolate the vault; **do not delete evidence** | 24 hours |
| Assessment | Determine data classes, affected individuals, and whether notification is legally required; counsel consulted | 72 hours |
| Notification | Notify affected participants; notify authorities if required by applicable law | Per legal requirement |
| Remediation | Fix the cause, not the symptom; re-audit the control that failed | 30 days |
| Record | Written incident report retained with the audit log | 30 days |

**Non-negotiable:** the project does not conceal, minimise, or delay notification to protect its reputation. A concealed incident discovered later ends the project; a disclosed one usually does not.

## 10. Consent and withdrawal mechanics

- Consent text is versioned; every consent record stores the exact version.
- A material change to the protocol, the imaging behaviour, the retention period, or the law-enforcement position requires **re-consent**, not a notification email.
- Withdrawal stops future deployments immediately.
- On withdrawal, the participant may request deletion of their event and image records. Deletion is honoured except where a legal hold applies, and the exception is explained in writing.
- Withdrawal does not require a reason, and the project does not ask for one in a form that creates a record of refusal.
- The participant is told, in one sentence, what happens to data already collected. Not "it depends on the retention policy" — the actual sentence, quoted from this document.

## 11. Minors and bystanders

- **Never published (D-52).** An image that appears to depict a minor, or a person with no connection to the opening, is flagged at adjudication and withheld from release. Age is estimated from appearance and the rule errs toward withholding; some young adults will be withheld as a result, and that is accepted.
- **Withheld, then destroyed.** A withheld image is access-restricted to the Lead and one reviewer, kept only until the adjudication record is written, then deleted. The record retains the image hash, the category, the reviewers, and the date — not the image. A legal hold suspends deletion for the affected record only, is logged, and must carry an expiry date.
- **A bystander image is a field-of-view failure, not a routine event.** The camera sees nothing while the box is closed, so an uninvolved passer-by should not appear at all. Any such image is logged as a geometry failure and reviewed against §1; a repeat at one site suspends that site.
- **Transparency.** The number of images withheld under this section is published by category, without images. A suppression rule that cannot be counted is a rule that quietly expands.
- Images are not used as illustration in project communications beyond the published dataset itself.

## 12. Vendor and tooling requirements

Any service that touches participant data must support: named accounts, MFA, encryption at rest, an audit log the project can read, a documented deletion path, and a data-processing agreement where applicable. A free tier with no audit log is not acceptable for image data, regardless of convenience.

## 13. Pre-deployment control checklist

Evidence must be filed, not asserted. "Reviewed" without an artefact does not count.

| Control | Evidence required | Owner |
|---|---|---|
| Accounting controller named | Signed appointment, dated | — |
| Access matrix implemented | Account list with roles, MFA status screenshot-free attestation | — |
| Access matrix tested | Revocation drill under 1 hour, recorded | — |
| Device encryption verified | Stolen-device simulation: attacker with device cannot read prior images | — |
| Key custody established | Two-custodian record; offline key location stated | — |
| Retention configured | System configuration evidence; a deletion dry-run | — |
| Deletion verification | One completed manifest with sample result | — |
| Law-enforcement position approved | Counsel sign-off, dated | — |
| Consent text approved | Versioned document + reviewer name | — |
| Breach procedure rehearsed | Tabletop exercise notes with date | — |
| Publication suppression | Test run showing n < 5 suppression works | — |
| Stop rules adopted | Signed acknowledgement by Lead | — |

Until every row has evidence, the pilot is not ready for Phase 2.
