---
tags: [embedded-c-best-practices]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Build a multi-layer thermal fan control slice for a power converter firmware project:
1. `drvs/pwm/drvPwm.h` and `drvs/pwm/drvPwm.c`: a table-driven PWM driver initialized from a configuration table and supporting setting channel duty cycle.
2. `src/bsp/config/bspPwmCfg.h`, `src/bsp/config/bspPwmCfg.c`, `src/bsp/bspPwm.h`, and `src/bsp/bspPwm.c`: board configuration and board-level wrapper API for the cooling fan PWM channel.
3. `src/app/appThermal.h` and `src/app/appThermal.c`: an application state machine that reads temperature sensor voltage in millivolts, applies hysteresis (trips at >= 3000 mV to 100% fan duty, clears at <= 2700 mV back to 25% fan duty), and commands the cooling fan through the BSP.
4. Host unit tests and a link-time driver fake (`drvs/pwm/test/fake_drvPwm.c` and `tests/test_appThermal.c`) that verify hysteresis transitions and error handling on host `gcc`.
