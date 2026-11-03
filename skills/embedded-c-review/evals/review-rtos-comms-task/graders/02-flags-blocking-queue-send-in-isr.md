---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags calling the blocking non-`FromISR` `xQueueSend` inside `USART2_IRQHandler` (`[RTOS-ISR-01]`) and recommends `xQueueSendFromISR` paired with `portYIELD_FROM_ISR`
