# Cost Reduction Plan — Getting the Module Under $100

**Status:** Proposed build and budget. Prices are small-quantity estimates from current listings, not quotes.
**Related:** D-57 to D-65, [`PRELIMINARY_BOM.md`](PRELIMINARY_BOM.md), [`../design/HARDENING_PLAN.md`](../design/HARDENING_PLAN.md) §9

## 1. Result

| | Before | After | Change |
|---|---:|---:|---:|
| Parts per module | ~$120 | **~$76** | −37% |
| Per deployable module, with 30% spares | ~$156 | **~$99** | −37% |
| Ten modules | ~$1,560 | **~$990** | −$570 |
| Programme, 90 days, pro bono counsel | ~$3,000–5,400 | **~$2,300–4,700** | −$700 |

The module does not lose a feature to get there. Camera, cellular, GNSS, light trigger, movement logging, 30-day runtime and sealed enclosure all survive.

## 2. Where the money actually was

| Line | Before | After | Why it moved |
|---|---:|---:|---|
| MCU + camera | 15 | 11 | A finished dev board instead of a module plus support parts |
| Light sensor + accelerometer | 4 | 3 | One sensor and a cheap accelerometer |
| Storage | 6 | 6 | Unchanged; 32 GB is the cheapest per byte |
| Secure element | 2 | 0 | The ESP32-S3 does secure boot and flash encryption itself |
| Modem + antenna | 30 | 34 | Slightly more, but the new part includes GNSS, which was going to cost $15–25 more |
| Battery + protection | 12 | 9 | LiFePO4 18650 in a holder |
| Enclosure, mount | 18 | 7 | A tray inside the retail box, not a separate IP-rated enclosure |
| PCB + assembly | 25 | **0** | Nothing to assemble; the dev board arrives assembled |
| Harness, misc | 8 | 5 | Fewer connectors |
| Reed switch + magnet | — | 1 | New, for arming |
| **Total** | **120** | **76** | |

**The largest single saving is not a component.** It is deciding not to build a custom PCB yet. Twenty-five dollars a board at quantity twelve is mostly setup and assembly labour; an $11 dev board arrives tested, with the camera already mounted.

## 3. The five choices behind it

### 3.1 ESP32-S3 camera development board — about $11

Single-unit listings run from roughly $9 to $17 depending on supplier and whether the board is a bare module or a finished unit with USB. It has the camera interface, enough RAM for three frames, deep sleep, and secure boot. Chosen over a bare module because at ten units the engineering time costs more than the parts saved.

### 3.2 Quectel BG95-M3 — about $28 with a carrier

This is the important one. The BG95-M3 carries **FCC, PTCRB and AT&T certification**, and it has **integrated GNSS**. So it replaces both the modem line and the separate GNSS module that the displacement measurement was going to need. The separately-budgeted $15–25 for GNSS disappears.

### 3.3 1NCE lifetime SIM — $14 per device, ten years

500 MB and 250 SMS over ten years, which averages about 4 MB a month. Our estimate is a few megabytes a month, so it fits — with little headroom in a heavy month. This is one-time, not per quarter, which is why the connectivity line falls from $180 to $140 while covering ten years instead of three months.

### 3.4 A tray inside the retail box, not a separate enclosure

The outer package is already the thing that looks ordinary and gets left on a porch. A laser-cut or 3D-printed tray holds the board, cell and camera at the right angle, and the retail box provides the weather protection. Saves $11 and removes a whole class of "the enclosure doesn't look like a parcel" problems.

### 3.5 No custom PCB for the ten prototypes

Hand-assembled dev boards, wired to a BG95 carrier. Ugly, slightly bulky, and entirely adequate for ten units. Revisit only if bench testing shows the board cannot meet the power budget.

## 4. Revised bill of materials

| Item | Est. USD | Note |
|---|---:|---|
| ESP32-S3 camera dev board | 11 | OV2640; USB to be disabled |
| BG95-M3 module with carrier | 28 | FCC/PTCRB/AT&T certified, GNSS included |
| LTE and GNSS antennas | 6 | Small patch or wire antennas |
| 18650 LiFePO4 cell, holder, protection | 9 | ~1500 mAh class |
| microSD 32 GB | 6 | Cheapest per byte; one cycle of records |
| VEML7700-class light sensor | 2 | Interrupt output |
| Accelerometer | 1 | Movement logging only |
| Reed switch and magnet | 1 | Arming at placement |
| Tray, foam, mounting | 5 | Inside the retail box |
| Retail box, per deployment | 2 | Consumable |
| Wiring, connectors, misc | 5 | — |
| **Parts subtotal** | **~76** | |
| Spares and attrition (+30%) | 23 | Modules are expected to be lost |
| **Per deployable module** | **~99** | |

## 5. What the saving costs you

Cheap prototypes buy risk. These are the risks, stated rather than buried:

**Dev-board sleep current.** A dev board carries a USB bridge, a status LED, and a linear regulator that can leak tens of milliamps. That will destroy a 30-day cycle on a 1500 mAh cell. Measure sleep current before anything else. The fix is usually to cut the regulator and feed 3.3 V directly, or to remove the USB bridge — both of which mean the "dev board" becomes a hand-modified board, which is fine for ten units.

**The USB port violates HW-27.** No connector may be accessible while sealed. On prototypes, the connector is removed or potted. This is a manufacturing step, not a design detail.

**Module certification is not device certification.** The BG95-M3 is certified as a module. A host device still has to follow Quectel's integration instructions, and may need its own authorisation. At ten research units the practical risk is low, but it is not zero, and "the module had an FCC ID" is not the whole answer.

**The 1NCE allowance is close to the estimate.** Roughly 4 MB a month of headroom against a few MB of use. Monitor it. A top-up is cheap; a device that runs out of data mid-pilot is not.

**Dev boards are physically bigger.** The tray has to fit the retail box with the camera at the right height. Check this before ordering ten.

**No part here is quoted.** Every figure is a listing price at small quantity. Supplier quotes will move the total, probably by ±20%.

## 6. What would make us reverse a choice

| If this happens | Then |
|---|---|
| Sleep current cannot get under ~0.3 mA | Custom board or a trimmed dev board becomes necessary; add ~$15/module |
| BG95 carrier is unavailable or expensive | Reconsider a certified modem without GNSS and add a $10 GNSS module |
| 1NCE coverage is poor at the deployment addresses | Switch to a Hologram or carrier IoT plan at a few dollars a month |
| Face is not legible at one metre | Spend the savings on a better camera and lens; this is the one place not to economise |

## 7. Next step

Nothing here is validated. The next action is not to buy ten of everything — it is to buy **one** of each and measure three things: sleep current, time from light step to first frame, and whether a face is legible at one metre under porch lighting. Those three numbers decide whether the $99 module is real.
