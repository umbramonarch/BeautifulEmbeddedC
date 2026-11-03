---
type: llm
focus: trace
weight: 1
---

`src/bsp/config/bspSpiCfg.c` is updated for the `MCU-B` board wiring (`hwInstanceId = 1U`, `csPortId = 2U`, `csPin = 2U`, `isCsActiveLow = true`) while remaining `const` in `.rodata` Flash and paired with `_Static_assert`
