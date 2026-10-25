---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags the unbounded ADC hardware polling loop in `motor_ReadCurrent` (`while ((VENDOR_ADC1->SR & VENDOR_ADC_SR_EOC) == 0);`) and places it in its highest-priority (`Must fix`) category
