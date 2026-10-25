---
type: llm
focus: trace
weight: 1
---

Shared ISR state is qualified `volatile`, blocking ADC polling is removed from `TIM1_UP_IRQHandler`, and shared fault counter access is protected by a save/restore critical section or atomic access
