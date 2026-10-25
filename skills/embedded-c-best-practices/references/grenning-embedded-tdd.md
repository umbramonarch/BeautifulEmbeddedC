# James Grenning — Test-Driven Development for Embedded C (digest)

Source: *Test-Driven Development for Embedded C* by James W. Grenning (Pragmatic Bookshelf,
2011, ISBN 978-1-934356-62-3).
Read this when setting up dual-target builds (host `gcc` + target cross-compiler), writing
link-time test doubles (fakes and spies) without `#ifdef TEST` clutter, applying the Humble
Object pattern, or designing opaque handles / Abstract Data Types (ADTs).

## 1. Dual-Target compilation (`[GRENNING-DUAL-01]`)

Wait-for-hardware debugging (compile -> flash over SWD/JTAG -> set breakpoint -> stimulate
inputs by hand) takes minutes per iteration and cannot easily reproduce rare sensor faults,
ADC timeouts, or counter wrap-arounds.

- **`[GRENNING-DUAL-01]` (Compile portable layers on host `gcc` from day one):** Because
  `src/app/`, `src/config/`, `src/bsp/`, `libs/`, and public `drvs/<periph>/drv*.h` headers
  contain zero vendor SDK headers and zero inline MCU assembly, they compile natively on the
  host machine (`gcc -std=c11`) alongside the target cross-compiler (`arm-none-eabi-gcc` or
  `riscv64-unknown-elf-gcc`).
- **Two link sets from one source tree:**
  - **Target build (`make all`):** Compiles `src/app/*.c`, `src/bsp/*.c`, `libs/*/*.c`,
    `drvs/*/*.c`, and `drvs/vendor_sdk/*.c` into the MCU `.elf`.
  - **Host test build (`make test`):** Compiles `src/app/*.c`, `src/bsp/*.c`, `libs/*/*.c`,
    `tests/fakes/fake_*.c` (or `drvs/*/test/fake_*.c`), and `tests/test_*.c` into a fast native
    executable that runs in < 50 ms.

## 2. Link-Time Substitution seams (`[GRENNING-SEAM-01]`)

Grenning identifies three seams for decoupling embedded code from hardware: preprocessing seams
(`#ifdef`), function-pointer runtime seams, and **link-time seams**.

- **`[GRENNING-SEAM-01]` (Use link-time substitution instead of `#ifdef TEST`):** Never place
  `#ifdef UNIT_TEST` or `#ifdef TEST` inside production `.c` or `.h` files. Conditional
  compilation means the code you test on the host is not the code you ship on the MCU, and it
  violates NASA JPL Rule 8 (`[JPL-8]`). Instead, swap the implementation at **link time** by
  linking `fake_drv<Periph>.c` in place of `drv<Periph>.c`.
- **Why link-time seams beat function-pointer vtables in firmware:** Runtime vtables require
  function pointers, which NASA JPL Rule 9 (`[JPL-9]`) prohibits because indirect calls prevent
  static stack-depth and control-flow verification. Link-time substitution uses direct symbol
  calls against `drv<Periph>.h`, costing zero bytes of RAM/Flash and zero indirect jumps.

```c
/* drvs/adc/drvAdc.h — shared contract compiled into both target and host builds */
MUST_CHECK Status_e drvAdc_Init(const DrvAdcConfig_t * const configTable,
                                size_t numChannels);
MUST_CHECK Status_e drvAdc_ChannelReadMv(size_t channel,
                                         Millivolts_t * const outVoltage_mv);
```

```c
/* drvs/adc/test/fake_drvAdc.h — test-only control interface (never included by production) */
#include "drvAdc.h"

void fakeDrvAdc_Reset(void);
void fakeDrvAdc_SetChannelMv(size_t channel, Millivolts_t voltage_mv);
void fakeDrvAdc_InjectStatus(Status_e status);
uint32_t fakeDrvAdc_GetReadCallCount(size_t channel);
```

```c
/* drvs/adc/test/fake_drvAdc.c — linked instead of drvAdc.c in host `make test` */
#include "fake_drvAdc.h"

#define FAKE_ADC_MAX_CHANNELS (16U)

static const DrvAdcConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;
static Millivolts_t s_channelValues_mv[FAKE_ADC_MAX_CHANNELS];
static uint32_t s_readCount[FAKE_ADC_MAX_CHANNELS];
static Status_e s_injectedStatus = STATUS_OK;

void fakeDrvAdc_Reset(void) {
    s_configTable = NULL;
    s_numChannels = 0U;
    s_injectedStatus = STATUS_OK;
    for (size_t i = 0U; i < FAKE_ADC_MAX_CHANNELS; ++i) {
        s_channelValues_mv[i].mv = 0;
        s_readCount[i] = 0U;
    }
}

Status_e drvAdc_Init(const DrvAdcConfig_t * const configTable, size_t numChannels) {
    if ((configTable == NULL) || (numChannels == 0U) || (numChannels > FAKE_ADC_MAX_CHANNELS)) {
        return STATUS_ERR_NULL_PTR;
    }
    s_configTable = configTable;
    s_numChannels = numChannels;
    return STATUS_OK;
}

Status_e drvAdc_ChannelReadMv(size_t channel, Millivolts_t * const outVoltage_mv) {
    if (s_injectedStatus != STATUS_OK) {
        return s_injectedStatus;
    }
    if (s_configTable == NULL) {
        return STATUS_ERR_UNINITIALIZED;
    }
    if (outVoltage_mv == NULL) {
        return STATUS_ERR_NULL_PTR;
    }
    if (channel >= s_numChannels) {
        return STATUS_ERR_INVALID_CHANNEL;
    }
    s_readCount[channel]++;
    *outVoltage_mv = s_channelValues_mv[channel];
    return STATUS_OK;
}
```

## 3. Test-Double taxonomy (`[GRENNING-DOUBLE-01]`)

Keep test doubles simple, deterministic, and static:

1. **Dummy:** Satisfies a parameter signature when the object is unused.
2. **Stub:** Returns canned values (`fakeDrvAdc_SetChannelMv(0U, (Millivolts_t){ 3300 })`) so the
   caller can exercise normal and fault paths (`fakeDrvAdc_InjectStatus(STATUS_ERR_TIMEOUT)`).
3. **Spy:** Records parameters and call counts (`s_lastDuty`, `s_readCount`) for post-hoc
   assertions in the test (`assert(fakeDrvPwm_GetLastDuty(0U).permille == 750U)`).
4. **Fake:** Provides lightweight working behavior in RAM (e.g., an in-memory EEPROM array
   replacing SPI Flash hardware).

## 4. Humble Object pattern (`[GRENNING-HUMBLE-01]`)

Code that touches physical registers or CPU interrupt masks is hard to unit-test directly.
Squeeze all hardware access into a **Humble Object** (`drv*.c`) that contains **zero domain
policy, zero scaling curves, and zero state machines**, and pull all decision logic into
`src/app/`, `src/bsp/`, or `libs/`:

```c
/* BAD — domain thermistor math and over-temperature hysteresis buried inside drvAdc.c */
void drvAdc_PollThermalProtection(void) {
    while ((ADC1->SR & 1U) == 0U) {}
    uint32_t raw = ADC1->DR;
    if (raw > 3100U) {
        TIM1->CCR1 = 1000U; /* Untestable on host! */
    }
}

/* GOOD — pure state transition in appThermal.c (100% host-tested), humble driver below */
Status_e appThermal_Step(Millivolts_t tempSensor_mv, DutyPermille_t * const outFanDuty) {
    if (outFanDuty == NULL) {
        return STATUS_ERR_NULL_PTR;
    }
    if (tempSensor_mv.mv >= APP_THERMAL_TRIP_MV) {
        s_isTripped = true;
    } else if (tempSensor_mv.mv <= (APP_THERMAL_TRIP_MV - APP_THERMAL_HYST_MV)) {
        s_isTripped = false;
    } else {
        /* Inside hysteresis band: keep previous s_isTripped state */
    }
    outFanDuty->permille = s_isTripped ? 1000U : 250U;
    return STATUS_OK;
}
```

## 5. Opaque Handles & Abstract Data Types (`[GRENNING-ADT-01]`)

When a module manages multiple instances (`libs/ring_buf`, `libs/pid`, or multi-instance drivers)
and callers should not see its internal fields:

- **Option A — Caller-supplied state struct with private-by-convention fields** (suitable for
  pure `libs/` modules where static allocation size must be known to the caller).
- **Option B — Opaque pointer handle backed by a fixed `static` pool inside `.c`** (zero heap,
  100% layout encapsulation):

```c
/* In header: incomplete struct type */
typedef struct DrvUartInstance_s *DrvUartHandle_t;

/* In .c: fixed static pool — never malloc() ([JPL-3]) */
struct DrvUartInstance_s {
    uint32_t magicId;
    size_t channelIndex;
    bool isOpen;
};
static struct DrvUartInstance_s s_uartPool[DRV_UART_MAX_INSTANCES];
```

## 6. Four-Phase Test structure (`[GRENNING-TEST-01]`)

Structure every host unit test into four explicit phases (**Setup -> Exercise -> Verify ->
Teardown**) and test boundary conditions:

1. `NULL` pointer arguments and `0` counts (`STATUS_ERR_NULL_PTR`)
2. Calls before `*_Init()` (`STATUS_ERR_UNINITIALIZED`)
3. Out-of-range channels and physical unit boundaries (`1000U` permille vs. `1001U` permille)
4. Injected hardware faults (`STATUS_ERR_TIMEOUT`, `STATUS_ERR_HW_FAULT`)
5. Normal state transitions, hysteresis edges, and buffer wrap-around

## 7. Checklist

- [ ] Can `src/app/`, `src/bsp/`, and `libs/` compile with host `gcc` without any MCU SDK?
- [ ] Are there zero `#ifdef TEST` / `#ifdef UNIT_TEST` blocks inside production `.c`/`.h` files?
- [ ] Does every hardware driver have a matching link-time fake (`fake_drv*.c`) for host tests?
- [ ] Do host unit tests cover `NULL` pointers, uninitialized state, boundary values, and
      injected timeouts?
