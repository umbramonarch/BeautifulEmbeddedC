---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags the ISR safety issues in `TIM1_UP_IRQHandler` (`g_overcurrentFaults` lacking `volatile`/atomic protection and/or calling the blocking `motor_ReadCurrent` inside an ISR)
