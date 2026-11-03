---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags leaking `FreeRTOS.h`/`queue.h`/`semphr.h`/`task.h` and `"vendor_usart_hal.h"` into the public `comms_task.h` header (`[RTOS-SEAM-01]`, `[BENINGO-HDR-01]`)
