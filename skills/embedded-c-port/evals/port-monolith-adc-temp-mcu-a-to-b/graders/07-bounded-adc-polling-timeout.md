---
type: llm
focus: trace
weight: 1
---

The hardware ADC conversion polling loop is bounded by an explicit maximum cycle count and returns a timeout error status (`STATUS_ERR_TIMEOUT`) if `MCU_B_ADC_ISR_EOC_MASK` does not assert in time
