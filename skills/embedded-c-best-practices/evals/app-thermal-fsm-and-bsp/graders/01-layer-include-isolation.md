---
type: llm
focus: trace
weight: 1
---

Layer include boundaries are respected: `src/app/appThermal.c` and `appThermal.h` include `bspPwm.h` and config headers, never `drvPwm.h`, `bspPwmCfg.h`, or any vendor SDK header
