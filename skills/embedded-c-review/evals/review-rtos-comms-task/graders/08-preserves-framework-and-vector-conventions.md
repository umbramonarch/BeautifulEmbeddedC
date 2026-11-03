---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` respects RTOS and startup vector conventions by not demanding that `USART2_IRQHandler` be made `static` or renamed, and not flagging `(void)pvParameters;` or the task `for (;;)` superloop structure itself as a `[JPL-2]` defect
