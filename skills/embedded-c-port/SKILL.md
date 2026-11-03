---
name: embedded-c-port
description: >-
  Port Embedded C firmware across microcontroller vendors, instruction-set architectures
  (8/16-bit to 32-bit, AVR/MSP/PIC to Cortex-M or RISC-V), and vendor HAL/register SDKs into
  deterministic, vendor-neutral, host-testable C11. Use this skill whenever the user asks to
  port, migrate, retarget, or adapt firmware, peripheral drivers (ADC, PWM, SPI, I2C, UART,
  CAN, Timer, GPIO, DMA), board support packages, or monolithic legacy modules from one MCU or
  SDK to another, or when replacing direct register/HAL calls with a portable Beningo
  app/bsp/drv layer split. Pairs with embedded-c-best-practices and embedded-c-review.
---

# Embedded C cross-MCU porting

Port Embedded C firmware from a source microcontroller (`MCU-A`) to a target microcontroller
(`MCU-B`) without silently breaking timing, scaling math, interrupt atomicity, or error
recovery. Every port must separate the **physical domain contract** (what the product does in
millivolts, milliamps, hertz, milliseconds, and permille) from the **silicon mechanics** (how
a specific MCU's registers, clock trees, bit widths, and interrupt flags achieve it).

## 1. Understand the source MCU module before writing anything

Before editing or generating a single line of C, inventory the source module along four axes:

- **Separate physical contract from silicon mechanics.** Record the domain behavior that must
  remain identical on `MCU-B`: trip thresholds, hysteresis bands, debounce counts, control
  loop periods, and startup safe states. Never carry raw ADC counts (`0..1023`), timer tick
  counts, or pin numbers across an MCU boundary (`[BARR-UNIT-SUFFIX]`, `[MISRA-UNIT-WRAP]`).
- **Audit clock-tree and peripheral bus ratios.** Determine how `MCU-A` derives peripheral
  clocks (e.g., 16 MHz single bus vs. 168 MHz core with divided APB1/APB2 timer clocks) so baud
  rates, PWM carrier frequencies (`_hz`), and polling timeout counters scale accurately on
  `MCU-B`.
- **Map peripheral resolution and reference voltages.** A 10-bit ADC at $V_{\text{ref}} = 5000\text{ mV}$
  (`1023` full-scale) ported to a 12-bit ADC at $V_{\text{ref}} = 3300\text{ mV}$ (`4095`
  full-scale) changes raw counts by $3.9\times$. Convert raw counts to `Millivolts_t` or
  `DutyPermille_t` inside `drv*.c` so `src/bsp/` and `src/app/` see zero scaling change.
- **Inspect interrupt flag clearing semantics.** Many 8/16-bit and older 32-bit MCUs clear
  status flags via read-modify-write (`SR &= ~FLAG`), whereas modern 32-bit peripherals use
  write-1-to-clear (`ISR = FLAG`) or dedicated clear registers (`ICR = FLAG`). Carrying `|=`
  or `&=` onto a write-1-to-clear register accidentally clears every other pending interrupt!

## 2. Establish host characterization tests and link-time seams first

- **Lock down existing domain behavior on host `gcc` before touching `MCU-B` registers
  (`[GRENNING-DUAL-01]`, `[GRENNING-TEST-01]`).** Write or run host unit tests against the
  application/BSP logic using a link-time fake (`fake_drv<Periph>.c`) to capture exact boundary
  transitions (hysteresis turn-on/turn-off points, fault latching, invalid parameter rejection).
- **Use link-time substitution instead of `#ifdef MCU_A` / `#ifdef MCU_B` clutter
  (`[GRENNING-SEAM-01]`, `[JPL-8]`).** Never interleave `#ifdef TARGET_MCU_A` and `#ifdef
  TARGET_MCU_B` branches inside application, BSP, or driver functions. Isolate `MCU-B` silicon
  access inside `drvs/<periph>/drv<Periph>.c` and board wiring inside
  `src/bsp/config/bsp<Periph>Cfg.c`.

## 3. Architectural strategy: Case A (layered) vs. Case B (monolithic)

Choose the porting workflow that matches the starting codebase (`[BENINGO-ARCH-01]`):

| Starting Codebase | What Changes for `MCU-B` | What Must Have Zero Diff |
| --- | --- | --- |
| **Case A: Already layered (`app` / `bsp` / `drv`)** | Rewrite `drvs/<periph>/drv<Periph>.c` for `MCU-B` registers/SDK and update `src/bsp/config/bsp<Periph>Cfg.c` (`hwInstanceId`, clock/pin mapping, polarity). | `src/app/*`, `src/bsp/bsp*.h`, `src/bsp/bsp*.c`, `drvs/<periph>/drv*.h`, and `tests/test_app*.c` (`[BENINGO-HDR-01]`, `[BENINGO-BSP-02]`). |
| **Case B: Legacy monolithic `MCU-A` module** | Split into (1) vendor-free public `.h` headers with physical units, (2) pure domain/FSM logic (`app` or `*_core.c`), (3) `.rodata` `const` config table (`bsp*Cfg.c`), and (4) `MCU-B` driver (`drv*.c`) + host fake (`fake_drv*.c`). | Domain thresholds, hysteresis bands, debounce counts, and safety shutoff polarity. |

- **Keep every `.h` file 100% vendor-free (`[BENINGO-HDR-01]`).** Neither `vendor_mcu_a.h` nor
  `vendor_mcu_b.h` (nor any `MCU_B_TypeDef *` register pointer) may appear in any `.h` file.
- **Name BSP APIs after the board schematic, never `MCU-A` or `MCU-B` pins
  (`[BENINGO-BSP-01]`).** Replace `mcuA_SetPortBPin3(1)` with `bspGpio_HeaterRelayEnable(true)`
  or a two-value enum so future board spins never ripple into `src/app/`.

## 4. Cross-MCU translation table & hardware pitfalls

Check every hardware interaction against these nine cross-MCU translation rules:

| Hazard / Feature | Legacy / `MCU-A` Pattern | Target `MCU-B` Compliant Pattern | Rule IDs |
| --- | --- | --- | --- |
| **Integer width & promotion** | Bare `int`, `unsigned`, or `long` (16-bit on AVR/MSP430/PIC, 32-bit on ARM/RISC-V, 64-bit on host LP64) | Fixed-width `<stdint.h>` types (`uint8_t`, `uint16_t`, `uint32_t`, `int32_t`, `size_t`) with `U` suffixes | `[BARR-5.2.a]`, `[MISRA-7.2]`, `[MISRA-10.1]` |
| **Floating-point scaling** | `float` / `double` voltage or temperature conversion (`raw * 5.0f / 1023.0f`) | 32-bit/64-bit integer fixed-point math in `Millivolts_t`, `Milliamps_t`, `DeciCelsius_t`, `DutyPermille_t` | `[MISRA-NO-FLOAT]`, `[MISRA-UNIT-WRAP]` |
| **ADC & PWM resolution** | Exposing raw 10-bit (`0..1023`) or 12-bit (`0..4095`) register counts to callers | Driver scales raw counts to physical units (`_mv`, `_permille`) using `const` config `vref_mv` / `resolutionBits` | `[BENINGO-CFG-01]`, `[BARR-UNIT-SUFFIX]` |
| **Register bit-fields** | C `struct { unsigned int en:1; unsigned int mode:2; }` overlaid on MMIO | Explicit `_POS` and `_MASK` macros with `UINT32_C()` shifts on `volatile uint32_t` registers | `[BARR-NO-BITFIELDS]`, `[BARR-5.3.b]` |
| **Interrupt / status clear** | Read-modify-write `SR &= ~FLAG` or `ISR \|= FLAG` on a W1C register | Direct assignment `REG_ISR = FLAG_MASK` (or write to dedicated `ICR`/`BCR` register) | `[BARR-1.8.c]`, `[BARR-6.5]` |
| **Polling loop timeouts** | Unbounded `while (!(SR & READY));` or fixed loop count assuming 8 MHz CPU | Bounded `for` loop up to `MAX_POLL_CYCLES` returning `STATUS_ERR_TIMEOUT` on expiry | `[JPL-2]`, `[JPL-7]`, `[MISRA-17.7]` |
| **ISR atomic shared state** | Bare multi-byte or RMW access (`g_faults++`), or unconditional `sei()`/`__enable_irq()` | `volatile` state + `irqState = SaveAndDisable()` / `Restore(irqState)` critical section | `[BARR-1.8.c]`, `[BARR-ISR-ATOMIC]` |
| **Endianness & struct layout** | Casting byte buffers `(Packet_t *)rxBuf` across 8/16/32-bit alignment rules | Explicit shift-and-mask byte serialization (`(uint16_t)((uint16_t)buf[0] << 8U) \| buf[1]`) | `[BARR-5.2.a]`, `[MISRA-10.3]` |
| **Pin polarity & wiring** | Hardcoded active-low/high bit flips scattered in application logic | `.isActiveLow` boolean in `const` `.rodata` config table paired with `_Static_assert` | `[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]` |

### Code pattern: Resolution-independent ADC scaling & W1C flag clearing in `drv*.c`

```c
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    STATUS_OK = 0,
    STATUS_ERR_NULL_PTR,
    STATUS_ERR_INVALID_PARAM,
    STATUS_ERR_TIMEOUT
} Status_e;

typedef struct {
    int32_t mv;
} Millivolts_t;

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t ISR; /* Write-1-to-clear (W1C) status register on MCU-B */
    volatile uint32_t DR;
} McuB_AdcRegs_t;

#define MCU_B_ADC_CR_START_MASK (UINT32_C(1) << 0U)
#define MCU_B_ADC_ISR_EOC_MASK  (UINT32_C(1) << 2U)
#define DRV_ADC_MAX_POLL_CYCLES (10000U)

static Status_e ConvertRawToMillivolts(uint32_t rawCounts,
                                       uint32_t vref_mv,
                                       uint8_t resolutionBits,
                                       Millivolts_t * const out_mv) {
    if ((out_mv == NULL) || (resolutionBits == 0U) || (resolutionBits > 16U)) {
        return STATUS_ERR_INVALID_PARAM;
    }
    uint32_t const fullScale = (UINT32_C(1) << resolutionBits) - 1U;
    if (rawCounts > fullScale) {
        return STATUS_ERR_INVALID_PARAM;
    }
    /* 64-bit intermediate prevents overflow at 16-bit resolution and 5000 mV Vref */
    uint64_t const scaled_mv =
        ((uint64_t)rawCounts * (uint64_t)vref_mv + ((uint64_t)fullScale / 2ULL)) /
        (uint64_t)fullScale;
    out_mv->mv = (int32_t)scaled_mv;
    return STATUS_OK;
}

static Status_e PollAndReadChannelMv(McuB_AdcRegs_t * const regs,
                                     uint32_t vref_mv,
                                     uint8_t resolutionBits,
                                     Millivolts_t * const out_mv) {
    if ((regs == NULL) || (out_mv == NULL)) {
        return STATUS_ERR_NULL_PTR;
    }
    /* Clear stale EOC flag via direct assignment (never '|=' on a W1C register) */
    regs->ISR = MCU_B_ADC_ISR_EOC_MASK;
    regs->CR |= MCU_B_ADC_CR_START_MASK;

    for (uint32_t cycle = 0U; cycle < DRV_ADC_MAX_POLL_CYCLES; ++cycle) {
        if ((regs->ISR & MCU_B_ADC_ISR_EOC_MASK) != 0U) {
            uint32_t const raw = regs->DR;
            regs->ISR = MCU_B_ADC_ISR_EOC_MASK;
            return ConvertRawToMillivolts(raw, vref_mv, resolutionBits, out_mv);
        }
    }
    return STATUS_ERR_TIMEOUT;
}
```

### Code pattern: `.rodata` polarity table, atomic GPIO set/clear, & byte-FIFO packing

```c
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

typedef enum {
    BSP_DIO_CH_HEATER_CUTOFF = 0,
    BSP_DIO_CH_FAULT_LED,
    BSP_DIO_CH_COUNT
} BspDioChannel_e;

typedef struct {
    uint32_t portId;
    uint8_t pinNumber;
    bool isActiveLow;
} DrvDioConfig_t;

typedef struct {
    volatile uint32_t BSRR; /* Bits 0..15 set pin; bits 16..31 reset pin atomically */
} McuB_GpioRegs_t;

static const DrvDioConfig_t kBspDioConfigTable[BSP_DIO_CH_COUNT] = {
    [BSP_DIO_CH_HEATER_CUTOFF] = { .portId = 1U, .pinNumber = 4U, .isActiveLow = true },
    [BSP_DIO_CH_FAULT_LED]     = { .portId = 1U, .pinNumber = 7U, .isActiveLow = false }
};

_Static_assert(ARRAY_LEN(kBspDioConfigTable) == (size_t)BSP_DIO_CH_COUNT,
               "kBspDioConfigTable size must match BspDioChannel_e count");

static void WritePinAtomic(McuB_GpioRegs_t * const port,
                           const DrvDioConfig_t * const cfg,
                           bool isAsserted) {
    if ((port == NULL) || (cfg == NULL) || (cfg->pinNumber >= 16U)) {
        return;
    }
    bool const driveHigh = cfg->isActiveLow ? (!isAsserted) : isAsserted;
    uint32_t const shift = driveHigh ? (uint32_t)cfg->pinNumber
                                     : ((uint32_t)cfg->pinNumber + 16U);
    port->BSRR = (UINT32_C(1) << shift);
}

static void PackBigEndianUint16(uint16_t frameWord, uint8_t outBytes[2]) {
    if (outBytes == NULL) {
        return;
    }
    outBytes[0] = (uint8_t)((frameWord >> 8U) & 0xFFU);
    outBytes[1] = (uint8_t)(frameWord & 0xFFU);
}
```

## 5. Keep the port proportionate

- **Preserve product thresholds and hysteresis exactly.** Do not silently alter trip points,
  debounce counts, or state machine transitions during a port unless the user explicitly asks
  for a behavior change.
- **Fix safety defects instead of porting bugs (`[JPL-1]`..`[JPL-10]`).** If the `MCU-A` code
  contains `malloc`/`free` (`[JPL-3]`), unbounded `while` loops (`[JPL-2]`), `goto`
  (`[JPL-1]`), unbraced control statements (`[BARR-1.3.a]`), or unprotected ISR shared state
  (`[BARR-ISR-ATOMIC]`), remediate those defects as part of the port and record each fix in
  `PORTING.md`.
- **Document silicon errata workarounds.** If `MCU-A` had a dummy register read or delay for a
  chip erratum that does not apply to `MCU-B` (or if `MCU-B` requires a dummy read after clock
  enable), document the change in `PORTING.md` rather than blindly copying or deleting it.

## 6. Verification gates

Before handing back a ported module or driver, run the verification pipeline when shell tools
are available:

```bash
# 1. Enforce mandatory braces and deterministic formatting
clang-format --dry-run -Werror src/**/*.[ch] drvs/**/*.[ch] libs/**/*.[ch]

# 2. Enforce vendor-free headers, layer #include boundaries, and NASA JPL safety rules
python3 lints/check_arch.py .

# 3. Compile and run host unit tests against link-time fakes with strict C11 warnings
gcc -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wsign-conversion \
    -Isrc/config -Isrc/bsp -Isrc/bsp/config -Isrc/app -Idrvs/<periph> -Idrvs/<periph>/test \
    src/app/*.c src/bsp/*.c src/bsp/config/*.c drvs/<periph>/test/fake_drv*.c tests/test_*.c \
    -o build/test_runner && ./build/test_runner
```

Verify every item on this checklist before finishing a port:

- [ ] Zero `MCU-A` or `MCU-B` vendor headers or register pointers in any `.h` file or upper
      layer (`[BENINGO-HDR-01]`, `[BENINGO-ARCH-01]`).
- [ ] For Case A (layered codebase), `src/app/*`, `src/bsp/bsp*.[ch]`, and `drv*.h` have zero
      functional diff (`[BENINGO-BSP-02]`).
- [ ] All peripheral and pin configuration tables are `const` in `.rodata` Flash and paired
      with `_Static_assert` size checks (`[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]`).
- [ ] All ADC, PWM, DAC, and timer scaling converts raw `MCU-B` register counts to fixed-width
      integer physical units (`_mv`, `_ma`, `_hz`, `_ms`, `_permille`, `_deci_c`) with zero
      `float`/`double` (`[MISRA-NO-FLOAT]`, `[MISRA-UNIT-WRAP]`).
- [ ] All status/interrupt clear operations respect `MCU-B` W1C vs. RMW semantics, and every
      hardware polling loop has an explicit cycle bound returning `STATUS_ERR_TIMEOUT`
      (`[JPL-2]`, `[BARR-1.8.c]`).
- [ ] All functions are <= 60 lines, use mandatory `{}` braces on every control block, and
      carry standardized `@file`/`@brief` and `//---...---//` banners (`[JPL-4]`,
      `[BARR-1.3.a]`, `[BENINGO-LAYOUT-01]`).

## 7. `PORTING.md` report template

Always deliver or update `PORTING.md` alongside ported code so hardware and firmware reviewers
can audit every register, scaling, and signature change:

~~~markdown
# Cross-MCU Porting Report: <Module or Driver Name> (`<MCU-A>` -> `<MCU-B>`)

## 1. Architectural Strategy
- **Port Type:** <Case A (Layered Driver/BSP Port) | Case B (Monolithic-to-Layered Split + Port)>
- **Unchanged Upper Layers:** <List files with zero diff, or state how domain logic was isolated>
- **New / Updated Target Files:** <List `drv*.c`, `bsp*Cfg.c`, and host test/fake files>

## 2. Peripheral & Register Mapping (`MCU-A` -> `MCU-B`)
| Function / Signal | `MCU-A` Register / Bit / SDK Call | `MCU-B` Register / Bit / SDK Call | Semantics / Pitfall Addressed |
| --- | --- | --- | --- |
| <e.g., ADC EOC Flag> | `ADC_SR` bit 1 (`&= ~EOC` RMW) | `ADC1->ISR` bit 2 (`ISR = EOC_MASK`) | Direct W1C assignment prevents clearing sibling flags |

## 3. Clock, Resolution, and Physical Unit Scaling
| Quantity | `MCU-A` Representation | `MCU-B` Representation | Fixed-Point Conversion Formula |
| --- | --- | --- | --- |
| <e.g., Bus Voltage> | 10-bit raw (`0..1023` @ 5.0 V `float`) | 12-bit raw (`0..4095` @ 3300 mV) -> `Millivolts_t` | `(raw * 3300U + 2047U) / 4095U` |

## 4. Safety & Concurrency Remediations
- **`[Rule ID]` (`file:line`):** <Defect in `MCU-A` code and how the `MCU-B` port remediated it>

## 5. Public API Changes & Host Verification Seam
- **Signature Updates:** <Before -> After prototypes, or "Zero public signature changes (Case A)">
- **Host Verification:** <Exact `gcc` command and summary of unit/characterization tests run>
~~~

## References

Read the companion digests in `skills/embedded-c-best-practices/references/` when deeper rules
or templates are needed:

- `references/beningo-reusable-firmware.md`: 4-layer (`app`/`bsp`/`drv`/`vendor_sdk`) +
  vertical `libs/` architecture, `.rodata` `const` configuration tables, and 3 BSP touchpoints.
- `references/grenning-embedded-tdd.md`: dual-target compilation, link-time substitution with
  fakes and spies (zero `#ifdef TEST`), and Humble Object boundary separation.
- `references/nasa-jpl-power-of-10.md`: all 10 Holzmann rules (`[JPL-1]`..`[JPL-10]`), bounded
  hardware register polling loops, static memory allocation, and <= 60-line functions.
- `references/barr-c-coding-standard.md`: BARR-C:2018 naming conventions, unit suffixes,
  mandatory braces, `const`/`volatile` discipline, register shift/mask macros, and ISR safety.
- `references/misra-and-type-safety.md`: MISRA C Essential Type Model (Rules 10.1–10.8),
  zero-cost single-field physical unit structs, `_Static_assert` proofs, and `MUST_CHECK`.
