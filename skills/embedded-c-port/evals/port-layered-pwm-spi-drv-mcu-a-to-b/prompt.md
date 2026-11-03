---
tags: [embedded-c-port, embedded-c-best-practices]
max_turns: 35
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Port this layered SPI DAC firmware project from `MCU-A` (`drvs/vendor_sdk/vendor_mcu_a_spi.h`)
to `MCU-B` (`drvs/vendor_sdk/vendor_mcu_b_spi.h`).

On the new `MCU-B` target board:
- The external 12-bit SPI DAC is connected to **`MCU_B_SPI1`** (`hwInstanceId = 1U`), clocked
  from a **96 MHz** peripheral bus (`MCU_B_SPI_PCLK_HZ`), with a maximum DAC SCK frequency of
  **6 MHz** (`6000000 Hz`).
- The DAC Chip-Select (`CS`) signal is wired to **GPIO Port C Pin 2** (`csPortId = 2U`,
  `csPin = 2U`, active-low `isCsActiveLow = true`), controlled via `MCU-B`'s atomic `BSRR`
  register.
- Unlike `MCU-A`'s 16-bit `DR16` register, `MCU-B`'s SPI peripheral uses an **8-bit byte FIFO**
  (`TXDR8` / `RXDR8`) and a dedicated write-1-to-clear Interrupt Flag Clear Register (`IFCR`).
  Every 16-bit SPI word must be transmitted and received **MSB first** (high byte first, low
  byte second).

Follow the Beningo layered porting discipline: keep **zero diff** in `src/app/`,
`src/bsp/bspSpi.h`, `src/bsp/bspSpi.c`, and `drvs/spi/drvSpi.h`. Verify that existing host
application tests (`tests/test_appDacCtrl.c`) and new/updated `MCU-B` driver tests pass under
`gcc -std=c11`, run `check_arch.py` if available, and document the port in `PORTING.md`.

Input files: src/config/project_types.h, drvs/spi/drvSpi.h, drvs/spi/drvSpi.c,
drvs/spi/test/fake_drvSpi.h, drvs/spi/test/fake_drvSpi.c,
drvs/vendor_sdk/vendor_mcu_a_spi.h, drvs/vendor_sdk/vendor_mcu_b_spi.h,
src/bsp/config/bspSpiCfg.h, src/bsp/config/bspSpiCfg.c, src/bsp/bspSpi.h, src/bsp/bspSpi.c,
src/app/appDacCtrl.h, src/app/appDacCtrl.c, tests/test_appDacCtrl.c
