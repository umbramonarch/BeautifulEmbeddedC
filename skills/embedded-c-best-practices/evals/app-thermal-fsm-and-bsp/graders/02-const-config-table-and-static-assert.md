---
type: llm
focus: trace
weight: 1
---

`src/bsp/config/bspPwmCfg.c` defines the PWM configuration table as `const` (so it resides in `.rodata` Flash) and includes a `_Static_assert` verifying its element count equals the BSP PWM channel enum count
