# Firmware — Foundation Build

**Status:** Written, not compiled against the ESP32 toolchain in this repository, and **not run on hardware**. Treat every constant marked `TODO(measure)` as a placeholder, not a value.

**Related:** [`../docs/hardware/HARDWARE_REQUIREMENTS.md`](../docs/hardware/HARDWARE_REQUIREMENTS.md), [`../docs/hardware/CAMERA_SUBSYSTEM.md`](../docs/hardware/CAMERA_SUBSYSTEM.md), [`../docs/data/DATA_MODEL.md`](../docs/data/DATA_MODEL.md)

## 1. What this is

Firmware for the reusable monitoring module: an ESP32-S3 with an OV2640 camera, a VEML7700 light sensor inside the sealed cavity, an accelerometer, a reed switch for arming, and a Quectel BG95-M3 modem for LTE-M/NB-IoT and GNSS.

It implements the decision set as code rather than prose:

| Requirement | Where it lives |
|---|---|
| HW-23 — motion never starts a burst | `main.cpp`, `handle_motion()` has no camera call; the only caller of `capture_burst()` is the light path |
| HW-30 — no command path can initiate imaging | `capture_burst()` is `static` and reachable only from the deep-sleep wake path. There is no UART, BLE, or network handler in this build |
| HW-32 — arming, so carriage is not recorded | `arming.cpp` logic in `main.cpp`; events are discarded until the reed switch is armed |
| D-64 — 0 / 0.5 / 1.5 s burst | `config.h` `kBurstOffsetsMs`, with exposure bracketing |
| D-66 — explicit eviction, never silent overflow | `store.cpp` `store_evict_if_needed()` |
| DATA_MODEL §3 — event taxonomy | `records.h` `EventType`, matching the documented names exactly |

## 2. What is verified and what is not

**Verified:** nothing on hardware. This code has not been compiled here, because the ESP32 toolchain is not installed in this workspace and pulling it would be a gigabyte-scale download that cannot complete inside a single command.

**Must be measured before any of it is trusted:**

- Deep-sleep current of the chosen dev board. A development board carries a USB bridge and a regulator that can leak tens of milliamps, which will end a 30-day cycle on a 1500 mAh cell. The documented fix is to remove the regulator and feed 3.3 V directly.
- Light threshold and debounce window. `kLightThresholdLux` and `kLightDebounceMs` are guesses.
- Camera exposure behaviour when the lid opens onto a bright scene. The first frame is expected to be blown.
- Modem attach time, and whether the BG95 AT sequences below match the module's actual firmware revision.
- GNSS fix time and accuracy on a porch, indoors, and in a moving vehicle.
- Energy per fix and per upload, and the resulting 30-day projection.
- RTC oscillator drift, and therefore how often the device must sync to keep timestamps inside the analysis tolerance. The residual ppm in `config.h` is an assumption, not a measurement.

## 3. Structure

```
firmware/
├── platformio.ini          build configuration
├── partitions.csv          16 MB layout with a large LittleFS data partition
├── include/
│   ├── config.h            pins, thresholds, timings — all tunables in one place
│   ├── records.h           record schema and event taxonomy
│   ├── store.h             flash queue and eviction
│   ├── timebase.h          monotonic clock that survives deep sleep
│   └── modem.h             BG95 driver interface
└── src/
    ├── main.cpp            wake handling, state machine, capture, arming
    ├── records.cpp         JSON serialisation and record IDs
    ├── store.cpp           LittleFS queue with the eviction rule
    ├── timebase.cpp        drift measurement and uncertainty bounds
    └── modem.cpp           AT command driver, time, GNSS, HTTP upload
```

## 4. Design decisions worth knowing

**Deep sleep is the main loop.** `setup()` runs, handles one wake reason, then sleeps again. There is no `loop()`. This is what makes a 30-day cycle plausible on a single cell, and it is also why the code is structured as a dispatcher rather than a loop.

**The camera is never powered outside a burst.** Camera power is a GPIO-controlled load switch. `capture_burst()` turns it on, waits for settle, captures, and turns it off. Leaving it powered between events is the fastest way to fail the power budget.

**Eviction is logged, not silent.** When the buffer fills, `store_evict_if_needed()` deletes oldest-uploaded first. If nothing has been uploaded it deletes the oldest unsent record and increments a counter that is itself transmitted as a record. A silent drop would corrupt the denominator, which the analysis plan forbids.

**Time survives sleep, and carries its own error bar.** `millis()` and the ESP timer both restart on every wake, so neither can timestamp an event that happened while the CPU was asleep. The RTC timer keeps counting, so it is the monotonic base. It is also inaccurate, so `timebase.cpp` measures its rate at every network sync, smooths it, and applies the correction. Every record carries `clock_synced` and `clock_uncertainty_s` together; a record is flagged rather than discarded, and a wide bound tells the analysis it is ordering-only.

## 5. Building

```bash
cd firmware
pio run                 # build
pio run -t upload       # flash
pio device monitor      # serial, debug builds only
```

The production build defines no console. See HW-30: a device that accepts commands can be asked for images, so the deployable image has no command surface at all.

## 6. What is deliberately absent

- No audio path (HW-06).
- No video path (HW-07).
- No remote capture command, and no code structure that could accept one (HW-30).
- No BLE, no Wi-Fi, no USB in the production image (HW-27).
- No facial recognition or biometric processing of any kind.

These are not omissions to be filled in later. They are requirements, and adding any of them would invalidate the privacy position the project rests on.
