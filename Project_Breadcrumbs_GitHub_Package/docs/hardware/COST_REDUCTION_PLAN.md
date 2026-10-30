# Cost Reduction Plan — Getting the Module Under $90

**Status:** Proposed build and budget. Prices are small-quantity estimates from current listings, not quotes.
**Related:** D-57 to D-67, [`PRELIMINARY_BOM.md`](PRELIMINARY_BOM.md), [`../design/HARDENING_PLAN.md`](../design/HARDENING_PLAN.md) §9

## 1. Result

| | Before | After | Change |
|---|---:|---:|---:|
| Parts per module | ~$120 | **~$66** | −45% |
| Per deployable module, with 30% spares | ~$156 | **~$86** | −45% |
| Ten modules | ~$1,560 | **~$860** | −$700 |
| Programme, 90 days, pro bono counsel | ~$3,000–5,400 | **~$2,100–4,500** | −$900 |

Nothing required has been removed. Camera, cellular, GNSS, light trigger, movement logging, 30-day runtime and sealed housing all survive.

## 2. Where the money was

| Line | Before | After | Why it moved |
|---|---:|---:|---|
| MCU + camera | 15 | 12 | A finished 16 MB dev board instead of a module plus support parts |
| Light sensor + accelerometer | 4 | 3 | One sensor and a cheap accelerometer |
| Storage | 6 | **0** | On-board flash replaces the card and slot (D-66) |
| Secure element | 2 | 0 | The ESP32-S3 does secure boot and flash encryption |
| Modem + antenna | 30 | 32 | Slightly more, but the part includes GNSS, which would have cost $15–25 more |
| Battery + protection | 12 | 9 | LiFePO4 18650 in a holder |
| Enclosure, mount | 18 | 4 | Foam cutouts in the retail box, no tray (D-67) |
| PCB + assembly | 25 | **0** | Nothing to assemble; the dev board arrives assembled |
| Harness, misc | 8 | 5 | Fewer connectors |
| Reed switch + magnet | — | 1 | Arming |
| **Total** | **120** | **66** | |

**The largest saving is not a component.** Deciding not to build a custom PCB removes $25 a board at quantity twelve, almost all of it setup and assembly labour. The second is the enclosure: $18 for an IP-rated box becomes $4 of foam.

## 3. The seven choices behind it

1. **ESP32-S3 dev board with 16 MB flash — about $12.** Camera interface, deep sleep, secure boot, and enough storage for a cycle of events without a card slot.
2. **Quectel BG95-M3 — about $28 with a carrier.** FCC, PTCRB and AT&T certified, with **integrated GNSS**, so it replaces the modem line and the separate GPS receiver.
3. **1NCE lifetime SIM — $14 per device for ten years**, 500 MB.
4. **VEML7700-class light sensor — $2.** Interrupt output, settable threshold, no analogue tuning.
5. **18650 LiFePO4, ~1500 mAh — $9 with holder and protection.** Tolerates sealed-enclosure heat better than Li-ion.
6. **No microSD — $0.** 16 MB of flash holds roughly twenty events; a 30-day cycle with a few events will not fill it.
7. **Foam cutouts in the retail box — $4.** The box already provides structure and weather protection.

## 4. Revised bill of materials

| Item | Est. USD | Note |
|---|---:|---|
| ESP32-S3 camera board, 16 MB flash | 12 | OV2640; USB to be disabled |
| BG95-M3 module with carrier | 28 | FCC/PTCRB/AT&T certified, GNSS included |
| Combined LTE and GNSS antenna | 4 | Single part, two bands |
| 18650 LiFePO4 cell, holder, protection | 9 | ~1500 mAh class |
| VEML7700-class light sensor | 2 | Interrupt output |
| Accelerometer | 1 | Movement logging only |
| Reed switch and magnet | 1 | Arming at placement |
| Foam cutouts | 2 | Inside the retail box |
| Retail box, per deployment | 2 | Consumable |
| Wiring, connectors, misc | 5 | — |
| **Parts subtotal** | **~66** | |
| Spares and attrition (+30%) | 20 | Modules are expected to be lost |
| **Per deployable module** | **~86** | |

## 5. What the saving costs you

**Dev-board sleep current.** A dev board carries a USB bridge, a status LED, and a regulator that can leak tens of milliamps. That will end a 30-day cycle on a 1500 mAh cell. Measure it first; the usual fix is to remove the regulator and feed 3.3 V directly.

**The USB port violates HW-27.** No connector may be accessible while sealed. On prototypes it is removed or potted.

**Flash has no removable medium.** If uploads fail for a long stretch, the buffer fills and the oldest event has to be evicted. Twenty events is generous for this design, but the eviction rule must be written and logged rather than left to overflow.

**Module certification is not device certification.** The BG95-M3 is certified as a module; the host still follows Quectel's integration instructions and may need its own authorisation.

**1NCE's 500 MB is close to the estimate** at roughly 4 MB a month. Monitor and top up.

**Foam is less precise than a tray.** Camera alignment has to be fixed by the cutout geometry; check it before ordering ten.

**No part here is quoted.** Every figure is a listing price at small quantity; expect ±20% from suppliers.

## 6. The cost floor — what else could go

Everything here was considered. Only three were taken.

| Lever | Saving | What it costs | Verdict |
|---|---:|---|---|
| Drop microSD for on-board flash | $6 | 20-event buffer, eviction if offline | **Adopted** (D-66) |
| One combined LTE/GNSS antenna | $2 | Slightly worse GNSS sensitivity | **Adopted** (D-67) |
| Foam cutouts instead of a tray | $3 | Less precise camera alignment | **Adopted** (D-67) |
| Li-ion cell instead of LiFePO4 | $3 | Worse behaviour in a sealed box at 60 °C | Rejected |
| Classic ESP32-CAM instead of S3 | $5 | Higher sleep current, slower capture, weaker security | Rejected |
| Uncertified modem | $8–12 | Illegal to attach to US networks | Rejected |
| Smaller cell, 14500 at 800 mAh | $5 | Runtime margin gone; AT-09 at risk | Rejected |
| Buy modules from a broker | $5 | No traceability, possible counterfeits | Rejected |
| Lower image resolution | $0 | Face legibility is the entire point | Rejected |

**The floor is about $60 in parts.** Below that you are choosing which requirement to lose: certification, runtime, security, or image quality. The current $66 keeps all four and leaves the next $20 of savings for a decision that has a real reason behind it.

Two of the rejected levers are worth revisiting only with evidence: if measured sleep current is low, the classic ESP32-CAM becomes defensible and saves $5; if thermal testing shows the box stays under 45 °C, Li-ion becomes defensible and saves $3. Neither should be assumed.

## 7. Next step

Buy **one** of each and measure three things: sleep current, time from light step to first frame, and whether a face is legible at one metre under porch lighting. Those three numbers decide whether the $86 module is real. Ordering ten before that is how a cheap design becomes an expensive lesson.
