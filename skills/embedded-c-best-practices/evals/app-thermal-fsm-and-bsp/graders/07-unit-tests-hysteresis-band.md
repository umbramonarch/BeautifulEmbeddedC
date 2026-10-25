---
type: llm
focus: trace
weight: 1
---

`tests/test_appThermal.c` tests both the rising trip threshold (>= 3000 mV -> 1000 permille), the hysteresis band (between 2701 mV and 2999 mV retains prior state), and the falling recovery threshold (<= 2700 mV -> 250 permille)
