---
type: llm
focus: trace
weight: 1
---

`drvs/pwm/drvPwm.c` validates `configTable != NULL`, `numChannels > 0`, initialization state, `channel < s_numChannels`, and `duty <= 1000` permille before accessing table entries
