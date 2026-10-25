# Jacob Beningo — Reusable Firmware Development (digest)

Source: *Reusable Firmware Development: A Practical Approach to APIs, HALs and Drivers* by
Jacob Beningo (Apress, 2017, ISBN 978-1-4842-3296-5).
Read this when designing or refactoring firmware architecture across layers (`app`, `bsp`,
`config`, `drv`, `libs`), creating peripheral configuration tables in `.rodata` Flash, or
formatting `.h` and `.c` files with standardized Doxygen headers and section dividers.

## 1. Four-layer horizontal architecture + vertical `libs/`

Firmware that mixes application state machines, board pin numbers, and MCU register pokes in
the same `.c` file cannot be ported to a new microcontroller or tested on a PC. Split every
firmware codebase into four horizontal layers plus one vertical pure-library pillar:

```text
  +-------------------------------------------------------------------+
  | L1: src/app/ + src/config/                                        |
  |     Product state machines, control policy, domain constants      |
  +-------------------------------------------------------------------+
                  | calls                           | calls
                  v                                 v
  +-------------------------------+   +-------------------------------+
  | L2: src/bsp/ + src/bsp/config/|   | V: libs/                      |
  |     Board-meaningful API &    |   |    Pure vertical algorithms:  |
  |     const wiring tables       |-->|    PID, filters, ring_buf,    |
  +-------------------------------+   |    CRC, state tables.         |
                  | calls             |    Zero HW headers.           |
                  v                   +-------------------------------+
  +-------------------------------+                 ^
  | L3: drvs/<periph>/            |-----------------+
  |     Vendor-free drv*.h API;   |
  |     MCU register work in .c   |
  +-------------------------------+
                  | calls
                  v
  +-------------------------------+
  | L4: drvs/vendor_sdk/          |
  |     MCU HAL / DriverLib /     |
  |     CMSIS (never modified)    |
  +-------------------------------+
```

### Architectural rule codes

- **`[BENINGO-ARCH-01]` (Strict downward dependencies):** Every horizontal layer may only
  `#include` headers from its own layer, the immediately adjacent lower layer, `src/config/`,
  and `libs/`. Upward includes (`drv` -> `bsp`, `bsp` -> `app`) and layer-skipping includes
  (`app` -> `drv` or `app` -> `vendor_sdk`) are forbidden.
- **`[BENINGO-ARCH-02]` (Pure vertical `libs/`):** Modules in `libs/` implement reusable math,
  containers, and protocols (ring buffers, PID controllers, moving-average filters, CRC,
  packet codecs). They may only `#include` `<stdint.h>`, `<stdbool.h>`, `<stddef.h>`,
  `src/config/*.h`, and their own headers.
- **`[BENINGO-ARCH-03]` (Pure declarative `src/config/`):** Headers in `src/config/` define
  product-wide constants, shared status enums (`Status_e`), and physical unit wrapper types
  (`Millivolts_t`, `FreqHz_t`). They depend only on C standard integer headers.
- **`[BENINGO-HDR-01]` (Vendor-free public headers):** No `.h` file anywhere in `src/app/`,
  `src/bsp/`, `src/config/`, `libs/`, or `drvs/<periph>/drv*.h` may `#include` a vendor MCU
  header (`stm32*.h`, `driverlib.h`, `nrf*.h`, `esp_*.h`) or reference a vendor register type
  (`TIM_TypeDef *`, `GPIO_Regs *`). Vendor headers are confined strictly to `drvs/<periph>/*.c`.

```c
/* BAD — drvs/adc/drvAdc.h leaks vendor SDK types to every caller ([BENINGO-HDR-01]) */
#include "vendor_mcu_adc.h"
Status_e drvAdc_Init(ADC_TypeDef *regs, uint32_t channel);

/* GOOD — drvs/adc/drvAdc.h is 100% vendor-free and compiles on host gcc */
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"

typedef struct {
    uint32_t hwInstanceId;
    uint8_t hwChannelIndex;
    Millivolts_t referenceVoltage_mv;
} DrvAdcConfig_t;

MUST_CHECK Status_e drvAdc_Init(const DrvAdcConfig_t * const configTable,
                                size_t numChannels);
MUST_CHECK Status_e drvAdc_SampleReadMv(size_t channel,
                                        Millivolts_t * const outVoltage_mv);
```

## 2. Board Support Package (BSP) discipline

- **`[BENINGO-BSP-01]` (Board-meaningful API names):** Functions in `src/bsp/bsp<Periph>.h`
  must be named after the board's schematic net or domain function, never the MCU pin or timer
  number. If a PCB respin moves the fault LED from `PA11` to `PC4`, `bspGpio_FaultLedSet(bool)`
  remains unchanged while `bspGpio_SetPA11(bool)` forces edits across `src/app/`.
- **`[BENINGO-BSP-02]` (The 3 BSP touchpoints):** Whenever a peripheral driver API in
  `drvs/<periph>/drv<Periph>.h` is added or updated, three BSP locations must stay synchronized:
  1. `src/bsp/config/bsp<Periph>Cfg.h` and `bsp<Periph>Cfg.c` (channel enum + `const`
     configuration table)
  2. `src/bsp/bsp<Periph>.h` and `bsp<Periph>.c` (board-specific wrapper API)
  3. `src/bsp/bsp.c` (`bsp_Init()` bring-up order)

## 3. Configuration Table Pattern in `.rodata` Flash

- **`[BENINGO-CFG-01]` (Table-driven peripheral initialization):** Peripheral drivers (`drv*.c`)
  must never hardcode board pin numbers, baud rates, or PWM frequencies. Instead, the driver
  defines `Drv<Periph>Config_t` and accepts `const Drv<Periph>Config_t * const configTable` and
  `size_t numChannels` in `drv<Periph>_Init()`.
- **`[BENINGO-CFG-CONST]` (Flash `.rodata` storage):** Every configuration table defined in
  `src/bsp/config/bsp<Periph>Cfg.c` (or `src/app/`) must be qualified `const` so the linker
  places it in read-only Flash (`.rodata`), consuming **zero bytes of SRAM** and preventing
  runtime corruption.
- **`[BENINGO-CFG-GUARD]` (Driver table retention and bounds checking):** Inside `drv<Periph>.c`,
  store the table pointer and channel count in `static` variables (`s_configTable`,
  `s_numChannels`). Every driver entry point must check `(s_configTable == NULL)` and
  `(channel >= s_numChannels)` before indexing the table or touching hardware registers.

```c
/* drvs/adc/drvAdc.c — table validation and bounds guard */
static const DrvAdcConfig_t *s_configTable = NULL;
static size_t s_numChannels = 0U;

Status_e drvAdc_Init(const DrvAdcConfig_t * const configTable, size_t numChannels) {
    if ((configTable == NULL) || (numChannels == 0U)) {
        return STATUS_ERR_NULL_PTR;
    }
    for (size_t ch = 0U; ch < numChannels; ++ch) {
        if (configTable[ch].referenceVoltage_mv.mv <= 0) {
            return STATUS_ERR_INVALID_PARAM;
        }
    }
    s_configTable = configTable;
    s_numChannels = numChannels;
    return STATUS_OK;
}
```

## 4. Standardized `.h` and `.c` file layout

- **`[BENINGO-LAYOUT-01]` (Doxygen file header and section banners):** Every `.h` and `.c` file
  across `app`, `bsp`, `config`, `drv`, and `libs` starts with a Doxygen `@file` and `@brief`
  banner and uses uniform `//---...---//` section dividers in a fixed order:
  - **`.h` files:** `Includes` -> `Exported Macros` -> `Exported Types` -> `Exported Variables`
    -> `Exported Prototypes`.
  - **`.c` files:** `Includes` (own `.h` first) -> `Private Macros` -> `Private Types` ->
    `Private Variables` -> `Private Prototypes` -> `Implementation`.
- **`[BENINGO-DOC-01]` (Contract documentation on public prototypes):** Every function prototype
  in a `.h` file carries a Doxygen comment specifying `@brief`, `@param` (with physical units
  and valid bounds), and `@return` (listing `STATUS_OK` and error codes).

## 5. Documented deviations from Beningo's book examples

1. **No function-pointer callback registration in safety-critical drivers:** Beningo's book
   includes `Dio_CallbackRegister(cb, fn_ptr)`. Per NASA JPL Rule 9 (`[JPL-9]`), function
   pointers are avoided so the call graph and worst-case stack depth remain statically
   verifiable. Prefer explicit status polling or static ISR-to-ring-buffer dispatch.
2. **Const-correctness on both sides of the table pointer:** Where some book listings write
   `DioConfig_t *Config`, we require `const Drv<Periph>Config_t * const configTable` so the
   table stays in `.rodata` Flash and the pointer parameter cannot be accidentally reseated.

## 6. Checklist

- [ ] Does `src/app/` include only `src/bsp/bsp*.h`, `src/config/*.h`, and `libs/*.h`?
- [ ] Are all `.h` files 100% free of vendor SDK headers and register pointers?
- [ ] Are all `*ConfigTable` arrays qualified `const` and paired with `_Static_assert`?
- [ ] Do all `.h` and `.c` files have `@file`/`@brief` headers and ordered section dividers?
