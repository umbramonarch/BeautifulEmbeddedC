---
type: llm
focus: trace
weight: 1
---

ISR-shared fault state is qualified `volatile`, blocking ADC reads are removed from the ISR, and main-thread access to ISR-shared state uses a save/restore critical section (`mcuB_IrqSaveAndDisable` / `mcuB_IrqRestore`)
