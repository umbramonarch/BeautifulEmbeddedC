---
name: embedded-c-best-practices
description: >-
  Write deterministic, testable, safety-critical Embedded C (C11) across all firmware layers.
  Use this skill whenever you write, review, refactor, debug, or explain Embedded C code:
  application state machines (app), product and board configurations (config), Board Support
  Packages (bsp), peripheral drivers (drv), pure algorithmic libraries (libs), interrupt
  service routines (ISRs), build scripts, or host unit tests. Trigger on any mention of
  Embedded C, firmware, microcontrollers, bare-metal, RTOS, Cortex-M, RISC-V, .c/.h files,
  MMIO registers, DMA, ADC, PWM, UART, SPI, I2C, clang-tidy, or MISRA, even when the user
  does not ask for "best practices" or "idiomatic" code. Synthesized from Jacob Beningo's
  Reusable Firmware Development, James Grenning's Test-Driven Development for Embedded C,
  NASA JPL's Power of 10, Michael Barr's BARR-C:2018 Coding Standard, and the MISRA C
  Essential Type Model.
---

# Embedded C best practices

Write deterministic, portable, host-testable C11 following five industry authorities: Jacob
Beningo (*Reusable Firmware Development*), James Grenning (*Test-Driven Development for
Embedded C*), Gerard Holzmann (*NASA JPL Power of 10*), Michael Barr (*BARR-C:2018*), and the
*MISRA C Essential Type Model*. Detailed digests live in `references/` — read them on demand
when a task needs deeper rules or code templates. Where the sources disagree, this file says
which to follow and why.

## 1. Mindset

- **Build locked doors, not signs on the wall.** Prose comments ("pass <= 3300 mV", "do not
  include vendor headers") are ignored under deadline pressure. Encode every invariant in a C
  type, `_Static_assert`, compiler flag, or `check_arch.py` rule that fails the build.
- **Keep hardware and RTOS headers out of 80% of your codebase.** `src/app/`, `src/config/`,
  `src/bsp/`, and `libs/` have zero MCU register addresses or vendor SDK types. Only `drvs/*.c`
  touches silicon, and `src/app/*.h` stays free of RTOS kernel headers (`[RTOS-SEAM-01]`).
- **Design every C file to compile on two targets from day one.** Every module above `drvs/*.c`
  compiles cleanly on host `gcc` so state machines and error paths run in milliseconds.
- **Prefer static determinism over runtime flexibility.** Allocate all state and RTOS objects
  statically at compile time, bound every loop and blocking wait, and keep control flow flat.

## 2. Before you hand back code

When you have shell access and a project directory, run these checks before finishing:

```bash
# 1. Enforce mandatory braces and deterministic formatting
clang-format --dry-run -Werror src/**/*.[ch] drvs/**/*.[ch] libs/**/*.[ch]
# 2. Enforce architecture boundaries, .rodata const tables, and NASA JPL safety bans
python3 lints/check_arch.py .
# 3. Compile and run fast host unit tests with link-time fakes, then static analysis
make test && make tidy && make all
```

- **Never silence a warning by weakening compiler flags.** Fix the underlying sign conversion,
  missing prototype, or unused parameter. For intentionally unused callback or RTOS task
  parameters, cast explicitly with `(void)param;` at the top of the function body.
- **Keep warnings enforced in the build, not via `#pragma` scatter.** Suggest or copy the
  drop-in configs in `lints/` (`.clang-format`, `.clang-tidy`, `.clangd`, `Makefile`,
  `check_arch.py`, `scaffold.py` from https://github.com/umbramonarch/BeautifulEmbeddedC).

## 3. Architecture across all C files (`app`, `bsp`, `config`, `drv`, `libs`)

Firmware is organized into four horizontal layers plus one vertical pure-library pillar so
every file type has a single responsibility and strict `#include` boundaries
(`[BENINGO-ARCH-01]`):

| Layer / Directory | Responsibility | Allowed `#include`s | Forbidden `#include`s |
| --- | --- | --- | --- |
| `src/app/` | Product state machines, control loops, high-level policy | Own `.h`, `src/config/*.h`, `src/bsp/bsp*.h`, `libs/*.h`, `<stdint.h>`, `<stdbool.h>`, `<stddef.h>` | `src/bsp/config/*`, `drvs/*`, vendor SDK headers, `FreeRTOS.h`/`task.h` in `app*.h`, `<stdio.h>`, `<stdlib.h>` |
| `src/config/` | Product constants, shared status enums, physical unit structs | `<stdint.h>`, `<stdbool.h>`, `<stddef.h>`, own `.h` | `app`, `bsp`, `drvs`, `libs`, vendor SDK headers |
| `src/bsp/` | Board-meaningful hardware & RTOS seam API (`bspGpio_FaultLedSet`, `bspRtos_*`) | Own `.h`, `src/bsp/config/*.h`, `src/config/*.h`, `drvs/*/drv*.h`, `libs/*.h` | `src/app/*`, vendor SDK headers (BSP never touches MCU registers directly) |
| `src/bsp/config/` | `const` wiring and peripheral configuration tables in `.rodata` | Own `.h`, `src/config/*.h`, `drvs/*/drv*.h` | `src/app/*`, vendor SDK headers |
| `drvs/<periph>/` | Reusable MCU peripheral drivers (`drvPwm`, `drvAdc`, `drvUart`) | `src/config/*.h`, `libs/*.h`, vendor SDK headers **inside `drv*.c` only** | `src/app/*`, `src/bsp/*`, **vendor SDK headers inside any public `drv*.h`** |
| `libs/<name>/` | Pure vertical algorithms (PID, filters, CRC, ring buffers, state tables) | `<stdint.h>`, `<stdbool.h>`, `<stddef.h>`, `src/config/*.h`, own `.h` | `src/app/*`, `src/bsp/*`, `drvs/*`, vendor SDK headers |

- **Keep public `.h` headers 100% vendor-free (`[BENINGO-HDR-01]`).** No header in `src/app/`,
  `src/bsp/`, `src/config/`, `libs/`, or `drvs/<periph>/drv*.h` may `#include` a vendor SDK
  header (`stm32f4xx.h`, `driverlib.h`, `nrf_gpio.h`) or expose a hardware register pointer.
- **Name BSP functions after the board schematic, never MCU pin numbers (`[BENINGO-BSP-01]`).**
  Callers in `src/app/` use domain names (`bspGpio_GateDriverEnable(true)`,
  `bspPwm_BuckPhaseSetDuty(duty_permille)`), never `bspGpio_SetPA8(true)`.
- **Update all three BSP touchpoints together when changing a driver (`[BENINGO-BSP-02]`).**
  Synchronize (1) `src/bsp/config/bsp<Periph>Cfg.h/.c`, (2) `src/bsp/bsp<Periph>.h/.c`, and
  (3) `bsp_Init()`. In smaller standalone projects, keep the same `*_core.h/.c` vs. `*_hal.h/.c`
  separation.

## 4. Configuration tables and `.rodata` Flash discipline

- **Drive peripherals from `const` configuration tables, not `#define`s (`[BENINGO-CFG-01]`).**
  Define `Drv<Periph>Config_t` in `drv<Periph>.h` and pass a `const` table to `drv<Periph>_Init`:

```c
/* drvs/pwm/drvPwm.h — 100% vendor-free public header */
typedef struct {
    uint32_t hwInstanceId;
    FreqHz_t switchingFreq_hz;
    DutyPermille_t initialDuty_permille;
    bool isActiveLow;
} DrvPwmConfig_t;

MUST_CHECK Status_e drvPwm_Init(const DrvPwmConfig_t * const configTable,
                                size_t numChannels);
```

- **Qualify every configuration table `const` so it lands in `.rodata` Flash
  (`[BENINGO-CFG-CONST]`).** Mutable tables waste `.data` SRAM and risk pointer corruption. Pair
  every table with a `_Static_assert` matching the channel enum (`[MISRA-STATIC-ASSERT]`):

```c
/* src/bsp/config/bspPwmCfg.h */
typedef enum {
    BSP_PWM_CH_BUCK_HIGH = 0,
    BSP_PWM_CH_COOLING_FAN,
    BSP_PWM_CH_COUNT
} BspPwmChannel_e;

extern const DrvPwmConfig_t kBspPwmConfigTable[BSP_PWM_CH_COUNT];
```

```c
/* src/bsp/config/bspPwmCfg.c — lands in .rodata (0 bytes of SRAM) */
const DrvPwmConfig_t kBspPwmConfigTable[BSP_PWM_CH_COUNT] = {
    [BSP_PWM_CH_BUCK_HIGH] = {
        .hwInstanceId = 0U, .switchingFreq_hz = { .hz = 100000U },
        .initialDuty_permille = { .permille = 0U }, .isActiveLow = false
    },
    [BSP_PWM_CH_COOLING_FAN] = {
        .hwInstanceId = 1U, .switchingFreq_hz = { .hz = 25000U },
        .initialDuty_permille = { .permille = 200U }, .isActiveLow = false
    }
};

_Static_assert(ARRAY_LEN(kBspPwmConfigTable) == (size_t)BSP_PWM_CH_COUNT,
               "kBspPwmConfigTable size must match BspPwmChannel_e count");
```

- **Keep `src/config/` headers pure and declarative.** Place product tuning limits in
  `src/config/*Cfg.h` with unit suffixes (`#define APP_THERMAL_TRIP_MV (3100)`).

## 5. Opaque handles and module state

- **Allocate all module state and RTOS objects statically (`[JPL-3]`, `[MISRA-21.3]`,
  `[RTOS-STATIC-01]`).** Never call `malloc`, `calloc`, `realloc`, `free`, or dynamic RTOS APIs
  (`xTaskCreate`, `xQueueCreate`, `xSemaphoreCreateMutex`). Use `xTaskCreateStatic`,
  `xQueueCreateStatic`, and `xSemaphoreCreateMutexStatic` backed by fixed `static` buffers.
- **Hide mutable state inside `.c` as `static` variables (`[BARR-1.8.a]`).** Never expose
  mutable globals via `extern` in a header. For multi-instance modules, use channel enums or
  opaque handles backed by a fixed `static` pool (`[GRENNING-ADT-01]`):

```c
/* Inside drvPwm.c — private state hidden from all callers */
static const DrvPwmConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static bool s_isInitialized = false;
```

## 6. Types, physical units, and naming

### Naming conventions (`[BARR-6.1]` + `[BENINGO-NAME-01]`)

We combine BARR-C's module-prefix and unit-suffix discipline with Beningo's `module_ActionNoun`
separation:

| Kind | Convention | Examples |
| --- | --- | --- |
| Public functions | `module_ActionNoun()` | `appThermal_RunStep()`, `bspPwm_FanSetDuty()`, `drvAdc_ChannelReadMv()`, `ringBuf_PushByte()` |
| Private functions (`static` in `.c`) | `static` + `PascalCase` or `module_PrivAction()` | `static Status_e ValidateChannel(size_t channel)` |
| Struct / Enum types & constants | `PascalCase_t` / `PascalCase_e` / `UPPER_SNAKE_CASE` | `DrvPwmConfig_t`, `Status_e`, `STATUS_OK`, `ADC_POLL_TIMEOUT_CYCLES (10000U)` |
| File-scope `static` / `.rodata` `const` | `s_camelCase` / `kPascalCase` | `s_configTable`, `s_lastSample_mv`, `kBspPwmConfigTable` |
| Local variables & struct fields | `camelCase` + physical unit suffix | `busVoltage_mv`, `phaseCurrent_ma`, `period_us`, `duty_permille` |
| **Framework & vector exemptions** | Keep exact RTOS/startup signatures | `void vCommsTask(void *pvParameters)` (`(void)pvParameters;`), non-`static` `void USART2_IRQHandler(void)`, `HAL_UART_RxCpltCallback()` in `drv*.c` |

### Fixed-width types and zero-cost physical unit wrappers

- **Use `<stdint.h>`, `<stdbool.h>`, and `<stddef.h>` exclusively (`[BARR-5.2.a]`).** Never use
  bare `int`, `short`, `long`, or `unsigned` for data; use `uint8_t`..`uint64_t`, `int32_t`,
  `size_t`, and `bool`.
- **Ban `float` and `double` unless hardware FPU usage is explicitly required
  (`[MISRA-NO-FLOAT]`).** Use fixed-point integers with physical unit suffixes: `_mv`, `_ma`,
  `_uv`, `_hz`, `_ms`, `_us`, and `_permille` (`0..1000` = `0.0%..100.0%`).
- **Wrap distinct physical units in single-field structs (`[MISRA-UNIT-WRAP]`).** Under ARM
  AAPCS, RISC-V, and x86-64 ABIs, single-field structs <= 4 bytes pass in CPU registers with
  **zero** RAM/Flash overhead while rejecting swapped arguments at compile time:

```c
/* src/config/project_types.h */
typedef struct { uint32_t hz; }       FreqHz_t;
typedef struct { uint16_t permille; } DutyPermille_t; /* 0..1000 = 0.0%..100.0% */
typedef struct { int32_t  mv; }       Millivolts_t;
typedef struct { int32_t  ma; }       Milliamps_t;
typedef struct { uint32_t ms; }       Milliseconds_t;
typedef struct { uint32_t us; }       Microseconds_t;

_Static_assert(sizeof(FreqHz_t) == sizeof(uint32_t), "FreqHz_t must be 4 bytes");
_Static_assert(sizeof(Millivolts_t) == sizeof(int32_t), "Millivolts_t must be 4 bytes");
```

- **Respect the MISRA Essential Type Model (`[MISRA-10.1]`).** Never mix signed and unsigned
  operands (`[MISRA-10.4]`), never shift/mask signed types (`[BARR-5.3.b]`), append `U` to
  unsigned literals (`[MISRA-7.2]`), and prefer two-value enums over ambiguous `bool` params.

## 7. Errors, assertions, and contracts

- **Return an explicit status enum marked `MUST_CHECK` (`[JPL-7]` + `[MISRA-17.7]`).** Annotate
  fallible functions with `__attribute__((warn_unused_result))` so callers cannot ignore errors:

```c
#if defined(__GNUC__) || defined(__clang__)
#define MUST_CHECK __attribute__((warn_unused_result))
#else
#define MUST_CHECK
#endif

typedef enum {
    STATUS_OK = 0,
    STATUS_ERR_NULL_PTR,
    STATUS_ERR_INVALID_CHANNEL,
    STATUS_ERR_INVALID_PARAM,
    STATUS_ERR_TIMEOUT,
    STATUS_ERR_UNINITIALIZED,
    STATUS_ERR_BUFFER_FULL,
    STATUS_ERR_BUFFER_EMPTY,
    STATUS_ERR_HW_FAULT
} Status_e;
```

- **Validate every pointer, index, and range at function entry (`[JPL-5]` + `[JPL-7]`).** Check
  `NULL` pointers, `s_isInitialized`, channel bounds, and physical ranges before dereferencing:

```c
Status_e drvPwm_SetDuty(size_t channel, DutyPermille_t duty_permille) {
    if (!s_isInitialized || (s_configTable == NULL)) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if (channel >= s_numChannels) {
        return STATUS_ERR_INVALID_CHANNEL;
    }
    if (duty_permille.permille > 1000U) {
        return STATUS_ERR_INVALID_PARAM;
    }
    /* Safe to index s_configTable[channel] and write hardware registers */
    return STATUS_OK;
}
```

- **Keep assertions side-effect-free (`[JPL-5]`).** Never put state-mutating calls inside
  `ASSERT(...)`. Pair runtime guards with compile-time `_Static_assert` checks.

## 8. Control flow, bounded loops, and watchdog liveness

- **Keep control flow strictly acyclic (`[JPL-1]`).** Never use `goto`, `setjmp`, `longjmp`,
  VLAs, or recursion so worst-case stack depth is statically provable (`-Wstack-usage=128`).
- **Bound every hardware polling loop with a fixed timeout (`[JPL-2]`).** Unbounded register
  polls (`while ((UART_SR & TX_EMPTY) == 0U) {}`) freeze the MCU if a clock or bus faults:

```c
/* BAD — hangs forever if peripheral clock or bus faults */
while ((ADC_REG_SR & ADC_SR_EOC_MASK) == 0U) {}

/* GOOD — bounded loop with explicit timeout and recovery path ([JPL-2]) */
Status_e WaitAdcReady(uint32_t maxCycles) {
    for (uint32_t cycle = 0U; cycle < maxCycles; ++cycle) {
        if ((ADC_REG_SR & ADC_SR_EOC_MASK) != 0U) {
            return STATUS_OK;
        }
    }
    return STATUS_ERR_TIMEOUT;
}
```

- **Bound RTOS task waits and use a rendezvous watchdog (`[RTOS-WDT-01]`).** RTOS task
  superloops (`for (;;)`) are valid when every iteration yields via a finite-timeout OS call
  (`pdMS_TO_TICKS(50U)`). Never block indefinitely with `portMAX_DELAY` / `K_FOREVER` in
  watchdog-monitored tasks, and feed the hardware watchdog only from a supervisor task after
  verifying all task heartbeat flags within the window.
- **Keep functions <= 60 lines (`[JPL-4]`), nesting <= 2–3 levels (`[BARR-8.2.b]`), mandatory
  `{}` braces on every control block (`[BARR-1.3.a]`), and a `default:` in every `switch`
  (`[BARR-8.3.b]`, `[MISRA-16.4]`).**

## 9. Interrupts, `volatile`, atomic safety, and RTOS concurrency

- **Keep ISRs minimal and use only `FromISR` OS primitives (`[BARR-6.5]`, `[RTOS-ISR-01]`).**
  Acknowledge the interrupt flag, push to a lock-free buffer or call `xQueueSendFromISR` /
  `vTaskNotifyGiveFromISR`, and yield via `portYIELD_FROM_ISR()`. Never call blocking OS APIs
  (`xQueueSend`, `xSemaphoreTake`, `vTaskDelay`) inside an ISR. Linker vector handlers
  (`void USART2_IRQHandler(void)`) must keep external linkage (never `static`).
- **Qualify MMIO and ISR-shared state `volatile` (`[BARR-1.8.c]`) and guard multi-word or RMW
  updates with save/restore critical sections (`[BARR-ISR-ATOMIC]`):** Never use an
  unconditional `__enable_irq()` that breaks nested callers:

```c
uint32_t bspTimer_FaultCountSnapshot(void) {
    uint32_t const irqState = bspIrq_SaveAndDisable();
    uint32_t const snapshot = s_isrFaultCount;
    bspIrq_Restore(irqState);
    return snapshot;
}
```

- **Use priority-inheriting mutexes for shared buses (`[RTOS-MUTEX-01]`).** Lock shared SPI/I2C/
  UART buses across tasks with `xSemaphoreCreateMutexStatic()` (with finite timeout), never a
  binary semaphore (which causes unbounded priority inversion).
- **Keep RTOS headers out of `src/app/*.h` (`[RTOS-SEAM-01]`).** Use the Humble Task Wrapper
  pattern: put pure state transitions in `app<Name>_Step()` (or behind `src/bsp/bspRtos.h`) so
  host `gcc` unit tests run without starting a FreeRTOS/Zephyr scheduler.
- **Never use C bit-fields to map hardware registers (`[BARR-NO-BITFIELDS]`).** Use explicit
  `_POS` and `_MASK` macros with `UINT32_C()` shifts.

## 10. Dual-target seams and host unit testing

- **Use link-time substitution instead of `#ifdef TEST` clutter (`[GRENNING-SEAM-01]`).**
  Compile `app`, `bsp`, and `libs` on host `gcc` and link against `fake_drv<Periph>.c` (or
  `fake_bsp*.c`) with zero `#ifdef UNIT_TEST` branches and zero function-pointer vtable overhead
  (`[JPL-9]`):

```c
/* drvs/pwm/test/fake_drvPwm.c — linked in place of drvPwm.c during host `make test` */
#include "drvPwm.h"

static DutyPermille_t s_lastDuty[16];
static uint32_t s_setDutyCallCount = 0U;
static Status_e s_injectedStatus = STATUS_OK;

Status_e drvPwm_SetDuty(size_t channel, DutyPermille_t duty_permille) {
    if (s_injectedStatus != STATUS_OK) {
        return s_injectedStatus;
    }
    if ((channel >= 16U) || (duty_permille.permille > 1000U)) {
        return STATUS_ERR_INVALID_PARAM;
    }
    s_lastDuty[channel] = duty_permille;
    s_setDutyCallCount++;
    return STATUS_OK;
}
```

- **Apply the Humble Object pattern (`[GRENNING-HUMBLE-01]`).** Keep `drv*.c` and RTOS task
  loops as thin executors; push hysteresis, PID math, framing, and watchdog supervision into
  host-tested `src/app/`, `src/bsp/`, or `libs/` modules.

## 11. Standardized file layout and Doxygen hygiene

Every `.h` and `.c` file follows a fixed section order with visual banners
(`[BENINGO-LAYOUT-01]` + `[BARR-4.3.b]`):

### Header file (`.h`) section order

```c
//-------------------------------------------------------------------------------------------------//
/**
 * @file        appThermal.h
 * @brief       Active thermal derating and fan control state machine
 */
//-------------------------------------------------------------------------------------------------//
#ifndef APP_THERMAL_H_
#define APP_THERMAL_H_

//-------------------------------------------------------------------------------------------------//
//             Includes
//-------------------------------------------------------------------------------------------------//
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

//-------------------------------------------------------------------------------------------------//
//             Exported Macros / Types / Variables / Prototypes
//-------------------------------------------------------------------------------------------------//

#endif /* APP_THERMAL_H_ */
```

### Source file (`.c`) section order

1. Doxygen `@file` and `@brief` banner
2. `Includes` (own `.h` first) -> `Private Macros` -> `Private Types` -> `Private Variables`
   (`static`) -> `Private Prototypes` (`static`) -> `Implementation`.
- **Document contracts (`@brief`, `@param` with units/bounds, `@return`) on public prototypes**
  and never leave commented-out code (`[BARR-2.1.c]`).

## 12. Compiler flags and static analysis

Always compile C11 firmware and host unit tests with the strict warning set (`[JPL-10]`):

```makefile
CFLAGS := -std=c11 -Os -g3 \
          -ffunction-sections -fdata-sections -fno-common \
          -Wall -Wextra -Werror -Wpedantic \
          -Wconversion -Wsign-conversion -Wdouble-promotion \
          -Wshadow -Wundef -Wformat=2 \
          -Wmissing-prototypes -Wstrict-prototypes -Wold-style-definition \
          -Wwrite-strings -Wcast-qual -Wvla -Wstack-usage=128
```

## 13. Final checklist

- [ ] Zero vendor SDK headers or register pointers in `.h` files or `app`/`bsp`/`config`/`libs`,
      and zero RTOS headers in `src/app/*.h` (`[BENINGO-HDR-01]`, `[RTOS-SEAM-01]`).
- [ ] All configuration tables are `const` in `.rodata` Flash and paired with `_Static_assert`
      (`[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]`).
- [ ] Zero dynamic allocation (`malloc`/`free`, `xTaskCreate`, `xQueueCreate`) and zero
      `<stdio.h>` in firmware (`[JPL-3]`, `[MISRA-21.3]`, `[RTOS-STATIC-01]`).
- [ ] Zero `goto`, `setjmp`/`longjmp`, VLAs, or recursion (`[JPL-1]`).
- [ ] Every hardware polling loop has a finite timeout (`[JPL-2]`), and every RTOS wait uses a
      bounded tick timeout with rendezvous watchdog supervision (`[RTOS-WDT-01]`).
- [ ] Every function is <= 60 lines, validates parameters at entry (`[JPL-4]`, `[JPL-5]`), and
      returns a `MUST_CHECK` status enum (`[JPL-7]`, `[MISRA-17.7]`).
- [ ] Fixed-width `<stdint.h>` types, unit suffixes (`_mv`, `_ma`, `_hz`, `_ms`, `_permille`),
      and single-field unit structs are used (`[BARR-5.2.a]`, `[MISRA-UNIT-WRAP]`).
- [ ] Mandatory `{}` braces on all control blocks and `default:` on all `switch` statements
      (`[BARR-1.3.a]`, `[BARR-8.3.b]`, `[MISRA-16.4]`).
- [ ] ISR-shared state is `volatile` with save/restore critical sections (`[BARR-ISR-ATOMIC]`),
      ISRs use only `FromISR` APIs (`[RTOS-ISR-01]`), and shared buses use priority-inheriting
      mutexes (`[RTOS-MUTEX-01]`).
- [ ] Standardized `@file`/`@brief` header and `//---...---//` banners appear in all files
      (`[BENINGO-LAYOUT-01]`, `[BARR-4.3.b]`), and host `gcc` tests pass via link-time fakes
      (`[GRENNING-SEAM-01]`).

## References

Load the matching digest from `references/` when a task needs deeper patterns or citations:

- `references/beningo-reusable-firmware.md`: 4-layer (`app`/`bsp`/`drv`/`vendor_sdk`) +
  vertical `libs/` architecture, `.rodata` `const` configuration tables, 3 BSP touchpoints, and
  standardized `.h`/`.c` file templates.
- `references/grenning-embedded-tdd.md`: dual-target compilation, link-time substitution with
  fakes and spies (zero `#ifdef TEST`), Humble Object split, and opaque handle pools.
- `references/nasa-jpl-power-of-10.md`: all 10 Holzmann rules (`[JPL-1]`..`[JPL-10]`), bounded
  hardware register polling loops, static memory pools, <= 60-line functions, and assertions.
- `references/barr-c-coding-standard.md`: BARR-C:2018 naming conventions, unit suffixes,
  mandatory braces, `const`/`volatile` discipline, register shift/mask macros, and ISR safety.
- `references/misra-and-type-safety.md`: MISRA C Essential Type Model (Rules 10.1–10.8),
  zero-cost single-field physical unit structs, `_Static_assert` proofs, and `MUST_CHECK`.
- `references/rtos-and-isr-frameworks.md`: static RTOS allocation (`[RTOS-STATIC-01]`),
  `FromISR` deferred interrupt handling (`[RTOS-ISR-01]`), priority-inheriting mutexes
  (`[RTOS-MUTEX-01]`), bounded blocking and watchdog supervision (`[RTOS-WDT-01]`), OS-agnostic
  Humble Task Wrappers (`[RTOS-SEAM-01]`), and framework/vector signature exemptions.
