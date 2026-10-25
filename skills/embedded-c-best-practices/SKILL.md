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

- **Build locked doors, not signs on the wall.** Prose comments ("caller must pass millivolts
  <= 3300", "do not include vendor headers here", "remember to check return status") are
  ignored under deadline and context pressure. Encode every invariant in a C type, a
  `_Static_assert`, a compiler flag, or an architecture script that fails the build at the
  exact `file:line`.
- **Keep hardware out of 80% of your codebase.** Application state machines (`src/app/`),
  product configurations (`src/config/`), board abstractions (`src/bsp/`), and utility
  libraries (`libs/`) should have zero knowledge of MCU register addresses or vendor SDK
  types. Only `.c` files inside `drvs/` touch silicon.
- **Design every C file to compile on two targets from day one.** Every module above the raw
  peripheral `.c` file must compile cleanly on host `gcc` (x86/ARM64) so its state machines,
  scaling math, and error paths can be verified in milliseconds without flashing hardware.
- **Prefer static determinism over runtime flexibility.** In safety-critical firmware, running
  out of heap, blocking on an unclocked peripheral flag, or overflowing the stack in a
  recursive helper is a catastrophic field failure. Allocate statically at compile time, bound
  every loop, and keep control flow flat.

## 2. Before you hand back code

When you have shell access and a project directory, run these checks before finishing:

```bash
# 1. Enforce mandatory braces and deterministic formatting
clang-format --dry-run -Werror src/**/*.[ch] drvs/**/*.[ch] libs/**/*.[ch]

# 2. Enforce architecture boundaries, .rodata const tables, and NASA JPL safety bans
python3 lints/check_arch.py .

# 3. Compile and run fast host unit tests with link-time fakes
make test

# 4. Run static analysis and cross-target compilation when toolchain is available
make tidy && make all
```

- **Never silence a warning by weakening compiler flags.** Fix the underlying sign conversion,
  missing prototype, or unused parameter. For intentionally unused callback or interface
  parameters, cast explicitly with `(void)param;` at the top of the function body.
- **Keep warnings enforced in the build, not via `#pragma` scatter.** The `BeautifulEmbeddedC`
  repo ships a ready-made set of configs in `lints/.clang-format`, `lints/.clang-tidy`,
  `lints/.clangd`, `lints/Makefile`, `lints/check_arch.py`, and `lints/scaffold.py`
  (https://github.com/umbramonarch/BeautifulEmbeddedC); suggest or copy them when a project
  has none.

## 3. Architecture across all C files (`app`, `bsp`, `config`, `drv`, `libs`)

Firmware is organized into four horizontal layers plus one vertical pure-library pillar so
that every file type has a single responsibility and strict `#include` boundaries
(`[BENINGO-ARCH-01]`):

| Layer / Directory | Responsibility | Allowed `#include`s | Forbidden `#include`s |
| --- | --- | --- | --- |
| `src/app/` | Product state machines, control loops, high-level policy | Own `.h`, `src/config/*.h`, `src/bsp/bsp*.h`, `libs/*.h`, `<stdint.h>`, `<stdbool.h>`, `<stddef.h>` | `src/bsp/config/*`, `drvs/*`, vendor SDK headers, `<stdio.h>`, `<stdlib.h>` |
| `src/config/` | Product constants, shared status enums, physical unit structs | `<stdint.h>`, `<stdbool.h>`, `<stddef.h>`, own `.h` | `app`, `bsp`, `drvs`, `libs`, vendor SDK headers |
| `src/bsp/` | Board-meaningful hardware API (`bspGpio_FaultLedSet`, `bspAdc_VbusReadMv`) | Own `.h`, `src/bsp/config/*.h`, `src/config/*.h`, `drvs/*/drv*.h`, `libs/*.h` | `src/app/*`, vendor SDK headers (BSP never touches MCU registers directly) |
| `src/bsp/config/` | `const` wiring and peripheral configuration tables in `.rodata` | Own `.h`, `src/config/*.h`, `drvs/*/drv*.h` | `src/app/*`, vendor SDK headers |
| `drvs/<periph>/` | Reusable MCU peripheral drivers (`drvPwm`, `drvAdc`, `drvUart`) | `src/config/*.h`, `libs/*.h`, vendor SDK headers **inside `drv*.c` only** | `src/app/*`, `src/bsp/*`, **vendor SDK headers inside any public `drv*.h`** |
| `libs/<name>/` | Pure vertical algorithms (PID, filters, CRC, ring buffers, state tables) | `<stdint.h>`, `<stdbool.h>`, `<stddef.h>`, `src/config/*.h`, own `.h` | `src/app/*`, `src/bsp/*`, `drvs/*`, vendor SDK headers |

- **Keep public `.h` headers 100% vendor-free (`[BENINGO-HDR-01]`).** No header in `src/app/`,
  `src/bsp/`, `src/config/`, `libs/`, or `drvs/<periph>/drv*.h` may `#include` a vendor HAL/SDK
  header (such as `stm32f4xx.h`, `driverlib.h`, or `nrf_gpio.h`) or expose a hardware register
  pointer. Leaking a vendor header into a `.h` poisons every upstream translation unit and
  makes host `gcc` compilation impossible.
- **Name BSP functions after the board schematic, never MCU pin numbers (`[BENINGO-BSP-01]`).**
  Callers in `src/app/` should read like domain logic (`bspGpio_GateDriverEnable(true)`,
  `bspPwm_BuckPhaseSetDuty(duty_permille)`), never `bspGpio_SetPA8(true)` or
  `bspTim1_SetCh1(500)`. When a board revision moves a signal from `PA8` to `PB12`, only
  `src/bsp/config/` changes; `src/app/` has zero diff.
- **Update all three BSP touchpoints together when changing a driver (`[BENINGO-BSP-02]`).**
  Whenever you add or modify a peripheral driver in `drvs/<periph>/`, update in the same
  change: (1) `src/bsp/config/bsp<Periph>Cfg.h/.c` (channel enum + `const` config table),
  (2) `src/bsp/bsp<Periph>.h/.c` (board-meaningful wrapper functions), and (3) your board's
  `bsp_Init()` bring-up sequence.
- **Write standalone modules with the same separation.** Even in a smaller project without full
  `app`/`bsp`/`drv` folders, split pure domain logic (`*_core.h/.c`) from hardware access
  (`*_hal.h/.c`) and keep all public headers free of vendor SDK includes.

## 4. Configuration tables and `.rodata` Flash discipline

- **Drive peripherals from `const` configuration tables, not hardcoded `#define`s
  (`[BENINGO-CFG-01]`).** A driver (`drvPwm.c`) should own zero board-specific knowledge.
  Define a `Drv<Periph>Config_t` struct in `drv<Periph>.h` and pass a pointer to a `const`
  table into `drv<Periph>_Init`:

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

- **Qualify every configuration table `const` so the linker places it in `.rodata` Flash
  (`[BENINGO-CFG-CONST]`).** SRAM is the scarcest resource on a microcontroller. A mutable
  configuration table is copied from Flash into `.data` SRAM at boot and can be corrupted by a
  stray pointer write. Pair every table with a compile-time `_Static_assert` proving its
  element count matches the channel enum (`[MISRA-STATIC-ASSERT]`):

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
        .hwInstanceId         = 0U,
        .switchingFreq_hz     = { .hz = 100000U },
        .initialDuty_permille = { .permille = 0U },
        .isActiveLow          = false
    },
    [BSP_PWM_CH_COOLING_FAN] = {
        .hwInstanceId         = 1U,
        .switchingFreq_hz     = { .hz = 25000U },
        .initialDuty_permille = { .permille = 200U },
        .isActiveLow          = false
    }
};

_Static_assert(ARRAY_LEN(kBspPwmConfigTable) == (size_t)BSP_PWM_CH_COUNT,
               "kBspPwmConfigTable size must match BspPwmChannel_e count");
```

- **Keep `src/config/` headers pure and declarative.** Product-level tuning parameters
  (overvoltage limits, control-loop periods, filter coefficients, fault debounce counts) belong
  in `src/config/*Cfg.h` as typed constants or `enum` values with physical unit suffixes
  (`#define APP_THERMAL_TRIP_MV (3100)`), never scattered as magic numbers in `.c` files.

## 5. Opaque handles and module state

- **Allocate all module state statically at compile time (`[JPL-3]`).** Never call `malloc`,
  `calloc`, `realloc`, or `free` in any layer. Heap allocation introduces non-deterministic
  execution time, fragmentation, and out-of-memory failures that cannot be proven safe.
- **Hide mutable state inside the `.c` file as `static` variables (`[BARR-1.8.a]`).** Never
  expose a module's internal state struct or global variables via `extern` in a header (the
  sole exception is a `const` configuration table declared in `bsp*Cfg.h`).
- **Use channel enums or opaque handles backed by a fixed `static` pool
  (`[GRENNING-ADT-01]`).** For multi-instance modules (`libs/ring_buf`, `libs/pid`, or
  multi-instance drivers), declare an incomplete struct pointer in the `.h` file (`typedef
  struct LibPid_s *LibPidHandle_t;`) or pass a bounded channel index, and keep the struct
  definition and fixed instance array `static` inside the `.c` file:

```c
/* Inside drvPwm.c — private state hidden from all callers */
static const DrvPwmConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static bool s_isInitialized = false;
```

## 6. Types, physical units, and naming

### Naming conventions (`[BARR-6.1]` + `[BENINGO-NAME-01]`)

*Note on source harmonization:* Beningo uses `Module_PascalCase` (`Dio_ChannelRead`,
`DioConfig_t`) while BARR-C uses `module_snake_case` (`adc_read`, `adc_config_t`). We combine
BARR-C's module-prefix and unit-suffix discipline with Beningo's clear visual separation between
the lowercase module prefix and the `ActionNoun` operation:

| Kind | Convention | Examples |
| --- | --- | --- |
| Public functions | `module_ActionNoun()` | `appThermal_RunStep()`, `bspPwm_FanSetDuty()`, `drvAdc_ChannelReadMv()`, `ringBuf_PushByte()` |
| Private functions (`static` in `.c`) | `static` + `PascalCase` or `module_ PrivAction()` | `static Status_e ValidateChannel(size_t channel)` |
| Struct & typedef types | `PascalCase_t` | `DrvPwmConfig_t`, `AppThermalState_t`, `FreqHz_t` |
| Enum types & values | `PascalCase_e` / `UPPER_SNAKE_CASE` | `Status_e`, `BspPwmChannel_e`, `STATUS_OK`, `STATUS_ERR_TIMEOUT` |
| Constants & macros | `UPPER_SNAKE_CASE` with `U` suffix on unsigned literals | `ADC_POLL_TIMEOUT_CYCLES (10000U)`, `ARRAY_LEN(a)` |
| File-scope `static` state | `s_camelCase` with unit suffix | `s_configTable`, `s_lastSample_mv`, `s_isInitialized` |
| `const` tables | `kPascalCase` | `kBspPwmConfigTable`, `kCrc8LookupTable` |
| Local variables & fields | `camelCase` + physical unit suffix | `busVoltage_mv`, `phaseCurrent_ma`, `period_us`, `duty_permille` |

### Fixed-width types and zero-cost physical unit wrappers

- **Use `<stdint.h>`, `<stdbool.h>`, and `<stddef.h>` exclusively (`[BARR-5.2.a]`).** Never use
  bare `int`, `short`, `long`, or `unsigned` for data — their bit widths vary across host x86
  (64-bit LP64/LLP64) and 16/32-bit MCU targets. Use `uint8_t`, `uint16_t`, `uint32_t`,
  `int32_t`, `size_t`, and `bool`.
- **Ban `float` and `double` unless hardware FPU usage is explicitly required
  (`[MISRA-NO-FLOAT]`).** On Cortex-M0/M0+/M3 and base RISC-V cores, a single accidental
  `double` literal pulls in kilobytes of soft-float library code and destroys deterministic
  timing. Represent fractional quantities with fixed-point integers in explicit physical units:
  millivolts (`_mv`), milliamps (`_ma`), microvolts (`_uv`), hertz (`_hz`), milliseconds
  (`_ms`), microseconds (`_us`), and permille (`_permille`, where `0..1000` = `0.0%..100.0%`).
- **Wrap distinct physical units in single-field structs (`[MISRA-UNIT-WRAP]`).** Under the ARM
  AAPCS and x86-64 System V ABIs, a single-field struct wrapping a 32-bit or 16-bit integer is
  passed directly in CPU registers (`r0`–`r3` / `rdi`–`rcx`) with **zero** RAM or Flash
  overhead, yet the C compiler rejects swapped arguments (`bspPwm_Configure(duty, freq)`) with
  a hard compile error:

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
  operands in arithmetic or comparisons, never use bitwise operators (`<<`, `>>`, `&`, `|`,
  `~`) on signed types (`[BARR-5.3.b]`), and append `U` to every unsigned integer literal
  (`0U`, `1000U`, `UINT32_C(1) << 15U`) (`[MISRA-7.2]`).
- **Avoid `bool` parameters in public APIs when meaning is unclear at the call site.** Prefer a
  two-value `enum` (`BspRelayState_e`) or separate functions (`bspRelay_Close(void)` /
  `bspRelay_Open(void)`) when `bspRelay_Set(true)` would be ambiguous.

## 7. Errors, assertions, and contracts

- **Return an explicit status enum marked `MUST_CHECK` (`[JPL-7]` + `[MISRA-17.7]`).** Every
  fallible function across `app`, `bsp`, `drv`, and `libs` returns a `Status_e` (or
  layer-specific status enum) annotated with `__attribute__((warn_unused_result))` so callers
  cannot silently ignore hardware timeouts or invalid arguments:

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

- **Validate every pointer, index, and range at function entry (`[JPL-5]` + `[JPL-7]`).** Every
  public function checks `NULL` pointers, `s_isInitialized`, channel bounds (`channel <
  s_numChannels`), and physical parameter bounds (`duty.permille <= 1000U`) **before**
  dereferencing pointers or touching hardware:

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

- **Keep assertions side-effect-free and active (`[JPL-5]`).** Never put state-mutating calls
  inside an `ASSERT(...)` macro. Pair runtime precondition checks with compile-time
  `_Static_assert` checks on array sizes, enum counts, and fixed-point scaling constants.

## 8. Control flow and bounded loops

- **Keep control flow strictly acyclic (`[JPL-1]`).** Never use `goto`, `setjmp`, `longjmp`,
  variable-length arrays (VLAs), or direct/indirect recursion in any firmware file. Acyclic
  control flow ensures that worst-case execution time (WCET) and maximum call-stack depth can
  be statically proven at compile time (`-Wstack-usage=128 -Wvla`).
- **Bound every loop with a fixed upper limit (`[JPL-2]`).** An unbounded hardware polling loop
  (`while ((UART_SR & TX_EMPTY) == 0U) {}`) will freeze the entire MCU if a peripheral clock is
  gated, a bus wire is shorted, or an external sensor fails. Every polling loop must decrement
  or increment against an explicit timeout constant and return `STATUS_ERR_TIMEOUT`:

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

- **Keep every function <= 60 lines (`[JPL-4]`).** Functions longer than 60 lines (excluding
  blank lines and comments) are hard to review and hide deep branching. Extract cohesive
  `static` helper functions and keep `if`/`else` nesting to at most 2–3 levels (`[BARR-8.2.b]`).
- **Put mandatory braces on every control statement (`[BARR-1.3.a]`).** Every `if`, `else`,
  `for`, `while`, `do`, and `switch` body must be enclosed in `{}` braces, even for a single
  statement. Configure `.clang-format` with `InsertBraces: true` and
  `AllowShortIfStatementsOnASingleLine: Never`.
- **Give every `switch` a `default:` clause (`[BARR-8.3.b]` + `[MISRA-16.4]`).** Handle
  unexpected enum values defensively in `default:` so corrupted memory cannot silently skip
  execution.

## 9. Interrupts, `volatile`, and atomic safety

- **Keep ISRs minimal: acknowledge, record, and exit (`[BARR-6.5]`).** An Interrupt Service
  Routine should clear the hardware interrupt flag, store the sample or push a byte into a
  lock-free ring buffer (`volatile` flag or SPSC queue), and return immediately. Never run
  filtering math, state machine transitions, or polling loops inside an ISR.
- **Qualify every MMIO register and ISR-shared variable `volatile` (`[BARR-1.8.c]`).** Without
  `volatile`, the compiler may hoist a register read out of a loop or eliminate repeated writes
  to a hardware control register.
- **Remember that `volatile` does not mean atomic (`[BARR-ISR-ATOMIC]`).** On a 32-bit MCU, a
  64-bit timestamp or a multi-field struct (and on an 8/16-bit MCU, even a 32-bit counter) or a
  read-modify-write (`s_sharedCount++`) can be torn across an interrupt boundary. Protect
  shared state between main thread and ISR using a critical section that saves and restores
  the interrupt mask (never an unconditional `enable_irq()` that breaks nested callers):

```c
uint32_t bspTimer_FaultCountSnapshot(void) {
    uint32_t const irqState = bspIrq_SaveAndDisable();
    uint32_t const snapshot = s_isrFaultCount;
    bspIrq_Restore(irqState);
    return snapshot;
}
```

- **Never use C bit-fields to map hardware registers (`[BARR-NO-BITFIELDS]`).** Bit-field
  ordering (MSB-first vs. LSB-first), alignment padding, and the width of the generated memory
  access instruction (`LDRB` vs. `LDR`) are implementation-defined by the C standard. Use
  explicit `_POS` and `_MASK` constants with `UINT32_C()` shifts.

## 10. Dual-target seams and host unit testing

- **Use link-time substitution instead of `#ifdef TEST` clutter (`[GRENNING-SEAM-01]`).**
  Never litter production `.c` files with `#ifdef UNIT_TEST` branches. Because `src/app/`,
  `src/bsp/`, `src/config/`, `libs/`, and `drvs/<periph>/drv*.h` are 100% free of vendor SDK
  headers, you can compile `app`, `bsp`, and `libs` with host `gcc` and link them against a
  test fake (`fake_drv<Periph>.c`) that implements the same `drv<Periph>.h` functions:

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

- **Why link-time substitution wins over function-pointer vtables (`[JPL-9]`):** NASA JPL Rule
  9 restricts function pointers because indirect calls defeat static call-graph and stack-depth
  verification. Link-time substitution gives you full test doubles (fakes and spies) with zero
  function pointers, zero `#ifdef TEST` macros, and zero RAM/Flash cost on the target MCU.
- **Apply the Humble Object pattern (`[GRENNING-HUMBLE-01]`).** Keep `drv*.c` as a thin,
  deterministic hardware executor (validate parameters, compute register masks, write MMIO).
  Push all state transitions, hysteresis, PID math, packet framing, and fault debouncing into
  `src/app/`, `src/bsp/`, or `libs/` where host unit tests exercise 100% of branches.

## 11. Standardized file layout and Doxygen hygiene

Every `.h` and `.c` file across `app`, `bsp`, `config`, `drv`, and `libs` follows a fixed
section order with clear visual section banners (`[BENINGO-LAYOUT-01]` + `[BARR-4.3.b]`) so any
engineer or static check can locate declarations immediately:

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
//             Exported Macros
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Types
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Variables
//-------------------------------------------------------------------------------------------------//

//-------------------------------------------------------------------------------------------------//
//             Exported Prototypes
//-------------------------------------------------------------------------------------------------//

#endif /* APP_THERMAL_H_ */
```

### Source file (`.c`) section order

1. Doxygen `@file` and `@brief` banner
2. `Includes` (always `#include` the module's own `.h` first to verify prototype match)
3. `Private Macros`
4. `Private Types`
5. `Private Variables` (`static` module state)
6. `Private Prototypes` (`static` helper declarations)
7. `Implementation` (public functions first, then `static` helpers)

- **Document contracts on every public prototype in `.h`.** State `@brief`, `@param` (including
  valid physical range and units), and `@return` (`STATUS_OK` and specific error codes). Never
  leave commented-out code in `.c` or `.h` files (`[BARR-2.1.c]`).

## 12. Compiler flags and static analysis

Always compile C11 firmware and host unit tests with the strict "locked-door" warning set
(`[JPL-10]`):

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

Before returning any Embedded C code, verify every item:

- [ ] Zero vendor SDK headers or register pointers in any `.h` file or in `app`, `bsp`,
      `config`, or `libs` (`[BENINGO-HDR-01]`).
- [ ] All configuration tables are `const` (in `.rodata` Flash) and paired with `_Static_assert`
      size checks (`[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]`).
- [ ] Zero dynamic allocation (`malloc`, `calloc`, `realloc`, `free`) and zero `<stdio.h>`
      formatting in firmware (`[JPL-3]`).
- [ ] Zero `goto`, `setjmp`/`longjmp`, VLAs, or recursion (`[JPL-1]`).
- [ ] Every hardware polling loop has an explicit timeout bound and returns
      `STATUS_ERR_TIMEOUT` (`[JPL-2]`).
- [ ] Every function is <= 60 lines and validates all pointers, channels, and ranges at entry
      (`[JPL-4]`, `[JPL-5]`).
- [ ] Every fallible function returns a `MUST_CHECK` status enum, and every caller checks it
      (`[JPL-7]`, `[MISRA-17.7]`).
- [ ] Fixed-width `<stdint.h>` types, physical unit suffixes (`_mv`, `_ma`, `_hz`, `_ms`,
      `_permille`), and single-field unit wrapper structs are used instead of bare `int` or
      `float` (`[BARR-5.2.a]`, `[MISRA-UNIT-WRAP]`).
- [ ] Mandatory `{}` braces wrap every `if`, `else`, `for`, `while`, `do`, and `switch` body
      (`[BARR-1.3.a]`).
- [ ] ISR-shared variables are `volatile` and multi-byte/RMW accesses are guarded by
      save/restore critical sections (`[BARR-1.8.c]`, `[BARR-ISR-ATOMIC]`).
- [ ] Standardized `@file`/`@brief` header and `//---...---//` section dividers appear in every
      `.h` and `.c` file (`[BENINGO-LAYOUT-01]`, `[BARR-4.3.b]`).
- [ ] Code compiles cleanly on host `gcc` with link-time fakes and zero `#ifdef TEST` clutter
      (`[GRENNING-SEAM-01]`).

## References

Load the matching digest from `references/` when a task needs deeper patterns, edge cases, or
specific rule citations:

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
