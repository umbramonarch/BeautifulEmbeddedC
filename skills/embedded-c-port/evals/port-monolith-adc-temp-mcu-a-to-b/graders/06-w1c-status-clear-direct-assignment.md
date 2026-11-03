---
type: llm
focus: trace
weight: 1
---

`MCU-B`'s write-1-to-clear ADC status flag (`MCU_B_ADC_ISR_EOC_MASK`) is cleared via direct assignment (`ISR = MCU_B_ADC_ISR_EOC_MASK`) rather than read-modify-write (`|=` or `&= ~`)
