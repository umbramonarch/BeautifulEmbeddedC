---
tags: [embedded-c-port, embedded-c-best-practices]
max_turns: 35
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Port the legacy 16-bit `MCU-A` thermistor temperature monitor (`ntc_monitor.h` and
`ntc_monitor.c`, currently written against `vendor_mcu_a_regs.h`) to the 32-bit `MCU-B`
hardware platform provided in `drvs/vendor_sdk/vendor_mcu_b_hal.h`.

Preserve the exact physical domain behavior across both thermistor channels (`ch 0` power
stage and `ch 1` battery pack):
- Linear NTC transfer curve: $T = 100.0\,^\circ\text{C} - (V_{\text{sense}} \times 20.0\,^\circ\text{C/V})$,
  i.e., $1000\text{ mV} \rightarrow 80.0\,^\circ\text{C}$ (`800 deci-degC`) and
  $1500\text{ mV} \rightarrow 70.0\,^\circ\text{C}$ (`700 deci-degC`).
- Channel 0 over-temperature trip at $80.0\,^\circ\text{C}$ (`800 deci-degC`) with hysteresis
  recovery at or below $70.0\,^\circ\text{C}$ (`700 deci-degC`); Channel 1 trip at
  $60.0\,^\circ\text{C}$ (`600 deci-degC`) with hysteresis recovery at or below
  $50.0\,^\circ\text{C}$ (`500 deci-degC`).
- Asserting the hardware heater cutoff output (`PB4`, active-low on `MCU-B`) whenever any
  channel is in an over-temperature fault state, and tracking over-temperature fault counts.

Refactor the module into clean, vendor-free, host-testable C11 (either a Beningo
`app`/`bsp`/`drv` split or a vendor-free module + `drv` seam), fix all memory, loop-bound,
type-safety, and ISR concurrency defects, verify with host `gcc` unit tests, and document the
register mapping, ADC resolution/voltage scaling, and signature changes in `PORTING.md`.

Input files: vendor_mcu_a_regs.h, ntc_monitor.h, ntc_monitor.c,
drvs/vendor_sdk/vendor_mcu_b_hal.h, drvs/vendor_sdk/vendor_mcu_b_hal.c
