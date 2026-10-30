# Prototype Test and Validation Plan

**Status:** Draft; bench testing must precede field deployment

## 1. Purpose

Verify that the prototype performs its stated functions reliably and safely before any participant deployment.

## 2. Test groups

### A. Light-trigger characterization
- Test controlled dark-to-light transitions.
- Test ambient light changes with the box closed and sealed, including direct sun on the lid.
- Test shadows and passing headlights.
- Test porch lights switching on/off.
- Test package movement without opening.
- Measure trigger latency and false-trigger frequency.
- Determine baseline, threshold, debounce, and lockout settings.

### B. Camera capture
- Measure time from validated trigger to first image.
- Measure actual interval between all three images.
- Confirm exactly three still images per qualifying event.
- Test focus and exposure at representative distances.
- Test daylight, shade, dusk, and expected porch-light conditions.
- Verify no audio capture and no continuous video mode.
- Attempt to initiate imaging through every available interface and confirm no command path exists.

### C. Storage and integrity
- Confirm each image maps to the correct module, deployment, and event.
- Test full-storage behavior.
- Test interrupted power during capture and write.
- Verify integrity checks and duplicate handling.
- Test encryption and access permissions.

### D. Power
- Measure standby current.
- Measure current during sensor sampling, camera wake, image capture, storage, and communications.
- Estimate runtime from measured duty cycle.
- Test low-battery reporting and safe cell replacement at a 30-day boundary.
- Confirm no charging or data connector is accessible while the unit is sealed.
- Run a full 30-day simulated cycle and compare projected against measured consumption.

### E. Communications and location
- Test offline buffering and later synchronization.
- Test failed and repeated uploads.
- Validate location accuracy and availability in representative conditions, including indoors and on a covered porch.
- Test fix acquisition time after a movement event and the energy cost per fix.
- Verify published location is reduced in precision and delayed as specified (D-41).

### F. Enclosure and environmental checks
- Check mounting stability and camera alignment.
- Test ordinary handling and vibration.
- Evaluate moisture and temperature exposure appropriate to intended deployment conditions.
- Inspect for light leaks that could create false triggers.
- Confirm serviceability and safe battery access.

### G. Operational workflow
- Run complete prepare-deploy-event-recover-inspect-reset cycles.
- Measure staff/participant time and maintenance burden.
- Test lost-device and participant-withdrawal procedures.
- Verify data access and deletion workflows.

## 3. Acceptance thresholds

Numeric acceptance thresholds must be set before testing and justified by pilot objectives. Do not invent pass rates after seeing results. Record:
- test setup;
- sample count;
- firmware/hardware revision;
- raw measurements;
- failures and anomalies;
- pass/fail decision;
- corrective action.

## 4. Field readiness gate

No field deployment until:
- all critical hardware defects are resolved;
- camera and trigger behavior is characterized;
- privacy/security review is complete;
- data access and retention are operational;
- participant materials are approved;
- legal and insurance review is complete;
- a documented incident response process exists.
