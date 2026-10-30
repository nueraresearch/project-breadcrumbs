# Radio, Spectrum, and SIM Options

**Status:** Analysis. D-68 keeps cellular; D-69 changes the pilot SIM to Hologram.
**Related:** [`CONNECTIVITY_OPTIONS.md`](CONNECTIVITY_OPTIONS.md), [`../../DECISION_LOG.md`](../../DECISION_LOG.md) D-58 to D-69

## 1. What the town actually decides

Presenting the pilot to the town is right. Presenting the *radio choice* to the town is not, because it isn't theirs to make.

The town's authority covers whether this happens in their community, and on what terms: permits, access, complaints, and the social licence to put cameras on porches. It does not cover spectrum — that is federal — and it does not cover which certified module sits inside the box.

So the framing matters. If you ask the town to choose between cellular and Wi-Fi, you invite a technical debate they have no way to resolve, and you hand a pressure group a proxy argument. If you tell them what the device does and ask them to approve the pilot, you get a decision they are actually equipped to make.

What they will really want to know, and what the governance documents already answer:

- What the camera sees, and when (only the inside of the box, only when opened — D-27).
- Who sees the images, and whether they get published (everyone; D-40, D-41, D-42, D-52).
- Whether the police get the data (research-only, compelled-process-only).
- What happens to a volunteer if something goes wrong.
- Whether the town is being used as a testbed without consent.

One sentence that helps: *the device uses a certified cellular module on commercial networks; it uses nothing belonging to the town.*

## 2. Spectrum: licensed versus unlicensed

| | Cellular LTE-M / NB-IoT | Wi-Fi 2.4 / 5 GHz | LoRa 902–928 MHz |
|---|---|---|---|
| Who holds the licence | The carrier | Nobody; Part 15 rules | Nobody; Part 15 rules |
| Do you need a licence | **No** | No | No |
| Typical range | Kilometres | Tens of metres | 1–10 km, with a gateway |
| Infrastructure required | None | Access points | A gateway you own |
| Fit for this device | **Yes** | No | No |

The device transmits under the carrier's licence. You are not applying for spectrum, and the town is not granting any. What you need is a certified module and a data plan.

That also disposes of a common worry at public meetings: this is not an unlicensed transmitter sitting on a porch at whatever power it likes. Power and frequencies are set by the network.

## 3. Certification: module versus device

The BG95-M3 holds FCC, PTCRB and AT&T certification. That does not automatically cover a device built around it, but it does most of the work.

- A certified module may be integrated **without a new FCC ID**, provided the conditions in its grant are met — antenna type and gain, co-location with other radios, labelling, and RF exposure.
- The host is still an unintentional radiator, so Part 15 verification applies in principle. For ten research units the practical risk is low; the legal requirement does not vanish because the run is small.
- **Action before assembly:** read the BG95-M3 grant and integration guide, and keep the antenna as specified. Deviating from the approved antenna is the usual way a certified module becomes an uncertified device.

This is also why the cheaper uncertified modems were rejected: the saving is $8–12, and the cost is a device that cannot legally attach to a US network.

## 4. SIM options

Prices are current listings, not quotes.

| Provider | Model | Ten devices, 90 days | Notes |
|---|---|---:|---|
| **Hologram** | $3 per SIM, $1/month per SIM, $0.03/MB | **~$63** | Cheapest for a short pilot; cancel anytime; per-MB pricing means no ceiling |
| 1NCE | $14 one-time, ten years, 500 MB | $140 | Cheapest long-run; ~4 MB/month average is close to our use |
| Soracom | ~$1/month plans with data bundles | ~$30–60 | Good tooling; US plan available; more setup than needed here |
| Carrier direct | Contract | Higher | Overkill for ten units |

**Recommendation: Hologram for the pilot.** Over 90 days it is roughly half the cost of 1NCE, there is no ten-year commitment, and paying by the megabyte removes the risk that a heavy month hits a 500 MB ceiling designed for a decade. If the study continues past a year, 1NCE becomes the better deal — $140 once versus $120 a year in platform fees alone.

Both work with the BG95-M3. The difference is commitment length, not capability.

## 5. What this changes

D-59 selected 1NCE on the assumption of a long-lived device. For a 90-day pilot that assumption costs money for nothing. D-69 records the change and keeps 1NCE as the option if the study extends.

## 6. Still open

- Confirm Hologram's plan supports LTE-M on the BG95-M3 band set (it should; verify before ordering SIMs).
- Physical nano-SIM or eSIM — the module supports both, and eSIM avoids a tray and a seal.
- Coverage test at three representative addresses before ordering ten of anything.
- Whether the town presentation mentions the carrier at all. Recommendation: mention that it is a commercial network and that no town infrastructure is used; do not open the choice.
