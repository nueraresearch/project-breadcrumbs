// config.h — every tunable in one place.
//
// Values marked TODO(measure) are placeholders. Do not treat any of them as a
// design figure; the hardware requirements are explicit that thresholds,
// debounce, lockout and fix interval must be set by measurement before field
// use (HARDWARE_REQUIREMENTS §5).

#pragma once

#include <stdint.h>

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

// Set per unit at provisioning. Must be unique (HW-02).
#ifndef BREADCRUMBS_MODULE_ID
#define BREADCRUMBS_MODULE_ID "MOD000"
#endif

#define FIRMWARE_REVISION "0.1.0-foundation"
#define HARDWARE_REVISION "1.2"

// ---------------------------------------------------------------------------
// Pins — TODO(verify): these assume a devkitc-1 carrier and a wired camera.
// Confirm against the actual board before trusting them.
// ---------------------------------------------------------------------------

#define PIN_LIGHT_INT       GPIO_NUM_4   // VEML7700 interrupt, active high
#define PIN_ACCEL_INT       GPIO_NUM_5   // LIS3DH INT1, active high
#define PIN_REED_SWITCH     GPIO_NUM_6   // closed = armed (D-63)
#define PIN_CAM_POWER       GPIO_NUM_7   // load switch for the camera rail
#define PIN_BATTERY_ADC     GPIO_NUM_8

#define PIN_I2C_SDA         GPIO_NUM_10
#define PIN_I2C_SCL         GPIO_NUM_11

// Modem UART
#define PIN_MODEM_TX        GPIO_NUM_17
#define PIN_MODEM_RX        GPIO_NUM_18
#define PIN_MODEM_PWRKEY    GPIO_NUM_12
#define PIN_MODEM_STATUS    GPIO_NUM_13

#define MODEM_BAUD          115200

// ---------------------------------------------------------------------------
// Light trigger
// ---------------------------------------------------------------------------

// The cavity is sealed and dark, so any sustained step is an opening. The
// threshold is therefore about noise, not about discriminating daylight.
#define kLightThresholdLux  40.0f    // TODO(measure)
#define kLightDebounceMs    200      // TODO(measure)
#define kTriggerLockoutMs   60000UL  // one event per opening, not per flicker

// ---------------------------------------------------------------------------
// Capture — D-64: 0 / 0.5 / 1.5 s, with exposure bracketing if supported.
// ---------------------------------------------------------------------------

#define kBurstFrameCount    3
static const uint32_t kBurstOffsetsMs[kBurstFrameCount] = {0, 500, 1500};

// Exposure bracketing. The first frame is expected to be blown when the lid
// opens onto a bright scene (CAMERA_SUBSYSTEM §4), so the three frames are
// deliberately spread across exposures rather than metered identically.
static const int kBurstExposures[3][2] = {
    // {aec_value, aec2 (0 = disable)}  TODO(measure) — OV2640 range is 0..1200
    {300, 0},
    {600, 0},
    {900, 0},
};

#define kCameraSettleMs     250      // TODO(measure) — regulator and clock ramp
#define kJpegQuality        12       // 0..63, lower is better quality
#define kFrameSize          FRAMESIZE_SVGA

// ---------------------------------------------------------------------------
// Movement — logged only, never images (HW-23, HW-24)
// ---------------------------------------------------------------------------

#define kMotionThresholdMg  80       // TODO(measure)
#define kMotionLockoutMs    5000UL   // debounce for the same bump

// ---------------------------------------------------------------------------
// Location — 4 fixes/day is the working assumption (HARDWARE_REQUIREMENTS §6)
// ---------------------------------------------------------------------------

#define kLocationIntervalMs (6UL * 60UL * 60UL * 1000UL)  // ~4/day
#define kLocationTimeoutMs  90000UL                        // TODO(measure)

// ---------------------------------------------------------------------------
// Upload
// ---------------------------------------------------------------------------

#define kUploadAttempts     3
#define kUploadRetryBaseMs  5000UL
#define kUploadRetryMaxMs   120000UL

// Flush budget per wake. Each frame is tens of kilobytes over LTE-M, so the
// flush is deliberately small: spending minutes awake to empty the queue costs
// more battery than it saves.
#define kMaxRecordsPerFlush 2
#define kMaxFramesPerFlush  6

// Telemetry endpoint. Not a command endpoint: it accepts POSTed records only,
// and nothing in the response can start a capture (HW-30).
#define kUploadHost         "ingest.example.invalid"
#define kUploadPath         "/v1/records"

// ---------------------------------------------------------------------------
// Timebase — see timebase.h
// ---------------------------------------------------------------------------

// Shorter gaps cannot measure the oscillator: the network's own resolution
// swamps the drift.
#define kMinIntervalForDriftS   600
// A disagreement larger than this means something jumped, not that the
// oscillator drifted. Rebase without touching the estimate.
#define kMaxPlausibleDriftS     86400
// Plausible range for a slow RC or crystal oscillator.
#define kMaxDriftPpm            200000
// Error bound before the drift has been measured, and after.
#define kResidualPpmCold        50000
#define kResidualPpmSteady      2000

// ---------------------------------------------------------------------------
// Power
// ---------------------------------------------------------------------------

#define kLowBatteryMv       3300     // TODO(measure) — LiFePO4 knee, verify
#define kBatteryDivider     2.0f     // 1:1 divider into the ADC
#define kAdcReferenceMv     3300

// ---------------------------------------------------------------------------
// Arming (HW-32, D-63)
// ---------------------------------------------------------------------------

// Sealing and placement take time; events during this window are the operator,
// not an opener. Discard until the reed switch reads armed.
#define kArmingStableMs     2000
