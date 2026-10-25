<!--
This review was produced by the embedded-c-review skill on the deliberately flawed motor
controller fixture in skills/embedded-c-review/evals/review-motor-ctrl/files/motor_ctrl.h
and motor_ctrl.c.
-->

# Embedded C review: `motor_ctrl.h` and `motor_ctrl.c`

`motor_ctrl.h` and `motor_ctrl.c` implement a DC motor current-limiting and PWM speed
controller that mixes **driver (`drv`)**, **board support (`bsp`)**, and **application (`app`)**
responsibilities in a single translation unit. **Verdict: Needs significant safety and
architectural fixes before use on hardware.** The single most important defect to fix is the
unbounded hardware register polling loop in `motor_ReadCurrent` (`motor_ctrl.c:42`), which will
permanently lock up the MCU if the ADC clock or conversion flag faults. Static inspection and
`python3 lints/check_arch.py` were run (`check_arch.py` flagged all architectural and safety
violations).

## Must fix

### 1. Unbounded hardware register polling loop can hang the MCU (`motor_ctrl.c:42`)
**Rule:** `[JPL-2]` Fixed upper bounds on all loops (NASA JPL Power of 10)
**Problem:** `while ((VENDOR_ADC1->SR & VENDOR_ADC_SR_EOC) == 0);` spins forever with no timeout
counter and no recovery path if the ADC peripheral clock is gated or the conversion fails to
complete.
**Fix:**
```c
#define MOTOR_ADC_TIMEOUT_CYCLES (10000U)

Status_e drvAdc_WaitReady(uint32_t maxCycles) {
    for (uint32_t cycle = 0U; cycle < maxCycles; ++cycle) {
        if ((VENDOR_ADC1->SR & VENDOR_ADC_SR_EOC) != 0U) {
            return STATUS_OK;
        }
    }
    return STATUS_ERR_TIMEOUT;
}
```

### 2. Vendor MCU SDK header and register pointer leaked into public `.h` (`motor_ctrl.h:4, 10`)
**Rule:** `[BENINGO-HDR-01]` Vendor-free public headers (Jacob Beningo, *Reusable Firmware
Development*) & `[GRENNING-DUAL-01]` Dual-Target compilation (James Grenning, *TDD for
Embedded C*)
**Problem:** `motor_ctrl.h` includes `"vendor_mcu_hal.h"` and exposes `VENDOR_TIM_Regs *timer`
inside `MotorConfig_t`. Every application file that includes `motor_ctrl.h` is now coupled to
silicon headers and cannot compile on host `gcc` for unit testing.
**Fix:**
```c
/* In motor_ctrl.h: remove #include "vendor_mcu_hal.h" and use a logical hardware ID */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
    uint32_t hwTimerInstanceId;
    FreqHz_t pwmFreq_hz;
    Milliamps_t maxCurrent_ma;
} DrvMotorConfig_t;
```

### 3. Dynamic heap allocation (`malloc`) in initialization (`motor_ctrl.c:20-24`)
**Rule:** `[JPL-3]` Zero dynamic memory allocation (NASA JPL Power of 10) & `[MISRA-21.3]`
**Problem:** `motor_Init` allocates runtime state with `malloc(sizeof(MotorRuntimeState) * 2)`,
introducing heap fragmentation, non-deterministic timing, and an unchecked `NULL` dereference
on lines 21–24 if the heap is exhausted.
**Fix:**
```c
static MotorRuntimeState_t s_runtimeState[MOTOR_MAX_CHANNELS];

Status_e drvMotor_Init(const DrvMotorConfig_t * const configTable, size_t numChannels) {
    if ((configTable == NULL) || (numChannels == 0U) || (numChannels > MOTOR_MAX_CHANNELS)) {
        return STATUS_ERR_NULL_PTR;
    }
    for (size_t i = 0U; i < numChannels; ++i) {
        s_runtimeState[i].lastDuty_permille.permille = 0U;
        s_runtimeState[i].isEnabled = true;
    }
    return STATUS_OK;
}
```

### 4. Configuration table is mutable in SRAM and lacks `_Static_assert` (`motor_ctrl.h:15`, `motor_ctrl.c:10-13`)
**Rule:** `[BENINGO-CFG-CONST]` Configuration tables in `.rodata` Flash (Beningo) &
`[MISRA-STATIC-ASSERT]` Compile-time table size proof
**Problem:** `MotorConfig_t g_motorConfig[2]` is declared without `const`, copying read-only
board wiring data into scarce SRAM (`.data`) where a stray pointer write can corrupt hardware
configuration, and lacks a `_Static_assert` tying its length to a channel enum.
**Fix:**
```c
typedef enum {
    BSP_MOTOR_CH_TRACTION = 0,
    BSP_MOTOR_CH_AUX,
    BSP_MOTOR_CH_COUNT
} BspMotorChannel_e;

const DrvMotorConfig_t kBspMotorConfigTable[BSP_MOTOR_CH_COUNT] = {
    [BSP_MOTOR_CH_TRACTION] = { .hwTimerInstanceId = 0U, .pwmFreq_hz = { 20000U }, .maxCurrent_ma = { 5000 } },
    [BSP_MOTOR_CH_AUX]      = { .hwTimerInstanceId = 1U, .pwmFreq_hz = { 20000U }, .maxCurrent_ma = { 2500 } }
};

_Static_assert(ARRAY_LEN(kBspMotorConfigTable) == (size_t)BSP_MOTOR_CH_COUNT,
               "kBspMotorConfigTable size must match BspMotorChannel_e count");
```

### 5. Non-atomic ISR shared counter and heavy work inside `TIM1_UP_IRQHandler` (`motor_ctrl.c:15, 64-70`)
**Rule:** `[BARR-1.8.c]` & `[BARR-ISR-ATOMIC]` ISR shared-data protection and minimal ISRs
(BARR-C:2018 Rules 1.8.c, 6.5)
**Problem:** `g_overcurrentFaults` is modified in `TIM1_UP_IRQHandler` and read/incremented in
`motor_Update` without `volatile` or a critical section, creating a read-modify-write data
race. In addition, the ISR calls `motor_ReadCurrent()` (which blocks on ADC conversion) directly
inside interrupt context.
**Fix:**
```c
static volatile uint32_t s_overcurrentFaultCount = 0U;
static volatile bool s_sampleReadyFlag = false;

void TIM1_UP_IRQHandler(void) {
    VENDOR_TIM1->SR &= ~VENDOR_TIM_SR_UIF;
    s_sampleReadyFlag = true; /* Defer ADC read and control update to main/task loop */
}

uint32_t motor_GetFaultCountSnapshot(void) {
    uint32_t const irqMask = bspIrq_SaveAndDisable();
    uint32_t const count = s_overcurrentFaultCount;
    bspIrq_Restore(irqMask);
    return count;
}
```

### 6. Use of `goto` for error cleanup (`motor_ctrl.c:55, 59`)
**Rule:** `[JPL-1]` Simple acyclic control flow — no `goto` (NASA JPL Power of 10 Rule 1,
BARR-C 1.7.c)
**Problem:** `motor_Update` jumps to `fail_shutdown:` using `goto`, violating acyclic control
flow rules.
**Fix:**
```c
if (current_ma.ma > s_configTable[channel].maxCurrent_ma.ma) {
    (void)drvMotor_EmergencyStop(channel);
    return STATUS_ERR_HW_FAULT;
}
```

## Should fix

### 7. Floating-point arithmetic and bare `int` types without physical units (`motor_ctrl.h:9-13, 18-20`, `motor_ctrl.c:27, 38, 45`)
**Rule:** `[BARR-5.2.a]` Fixed-width `<stdint.h>` types, `[MISRA-NO-FLOAT]`, &
`[MISRA-UNIT-WRAP]` Zero-cost physical unit wrappers
**Problem:** `motor_SetSpeed(int ch, float duty)` and `float max_current` use bare `int` and
single-precision `float` (`0.0f..1.0f`), pulling soft-float routines into integer MCUs and
allowing callers to swap channel, frequency, and duty arguments.
**Fix:**
```c
typedef struct { uint16_t permille; } DutyPermille_t;
typedef struct { int32_t  ma; }       Milliamps_t;

MUST_CHECK Status_e drvMotor_SetDuty(size_t channel, DutyPermille_t duty_permille);
```

### 8. Missing braces on single-line `if` statements (`motor_ctrl.c:28-31, 54-55`)
**Rule:** `[BARR-1.3.a]` Mandatory braces on every control block (BARR-C:2018 Rule 1.3.a)
**Problem:** Five `if` statements in `motor_SetSpeed` and `motor_Update` omit `{}` braces around
their bodies, making them prone to unconditional execution bugs during maintenance.
**Fix:**
```c
if (duty_permille.permille > 1000U) {
    return STATUS_ERR_INVALID_PARAM;
}
```

### 9. Fallible APIs return `void` or unchecked `int` (`motor_ctrl.h:18-21`, `motor_ctrl.c:52`)
**Rule:** `[JPL-7]` Check all non-void returns & `[MISRA-17.7]` `MUST_CHECK` status enum
**Problem:** `motor_Init` and `motor_Update` return `void`, hiding initialization and ADC
failures, while `motor_Update` ignores the return value of `motor_SetSpeed(ch, 0.0f)` on line
52.
**Fix:**
```c
#define MUST_CHECK __attribute__((warn_unused_result))

MUST_CHECK Status_e drvMotor_Init(const DrvMotorConfig_t * const configTable,
                                  size_t numChannels);
MUST_CHECK Status_e drvMotor_Update(size_t channel);
```

## Consider

### 10. Separate `app`, `bsp`, and `drv` layers and add standardized file banners (`whole file`)
**Rule:** `[BENINGO-ARCH-01]` 4-Layer Architecture & `[BENINGO-LAYOUT-01]` Standardized Doxygen
file banners
**Problem:** `motor_ctrl.c` combines low-level timer/ADC register access (`drv`), board channel
tables (`bsp/config`), and overcurrent trip policy (`app`) in one file without Doxygen
`@file`/`@brief` headers or section dividers, preventing host unit testing via link-time fakes.
**Fix:**
```c
//-------------------------------------------------------------------------------------------------//
/**
 * @file        drvMotor.h
 * @brief       Vendor-free PWM motor driver interface
 */
//-------------------------------------------------------------------------------------------------//
```

## What's already good

- **Include guards are present (`motor_ctrl.h:1-2, 23`):** `motor_ctrl.h` uses a clean
  `#ifndef MOTOR_CTRL_H` / `#define MOTOR_CTRL_H` guard.
- **Overcurrent fail-safe intent (`motor_ctrl.c:50-56`):** `motor_Update` explicitly forces PWM
  duty to zero when measured current exceeds the configured threshold rather than continuing to
  drive the power stage.
- **Upper and lower duty clamping check (`motor_ctrl.c:28-30`):** `motor_SetSpeed` checks both
  negative and >100% duty inputs before writing the timer compare register.

## Suggested lints

Copying the drop-in configs from [`lints/`](https://github.com/umbramonarch/BeautifulEmbeddedC)
into this project will enforce these rules automatically on every build:
- `python3 lints/check_arch.py .` immediately catches Finding 1 (`[JPL-2]` unbounded hardware
  loop), Finding 2 (`[BENINGO-HDR-01]` vendor header leaked in `.h`), Finding 3 (`[JPL-3]`
  `malloc`), Finding 4 (`[BENINGO-CFG-CONST]` non-`const` config table), Finding 6 (`[JPL-1]`
  `goto`), and Finding 7 (`float` usage).
- `clang-format --dry-run -Werror` with `lints/.clang-format` (`InsertBraces: true`) catches and
  auto-fixes Finding 8 (`[BARR-1.3.a]` unbraced `if` statements).
