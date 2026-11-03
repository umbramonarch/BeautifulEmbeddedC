---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags the dynamic RTOS heap allocations in `comms_Init` (`xQueueCreate`, `xSemaphoreCreateBinary`, and `xTaskCreate`) and recommends static RTOS allocation (`xQueueCreateStatic`, `xTaskCreateStatic`, `xSemaphoreCreateMutexStatic` under `[RTOS-STATIC-01]` or `[JPL-3]`)
