---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags the infinite `portMAX_DELAY` wait in `xQueueReceive` (and/or `xSemaphoreTake`) inside `vCommsTask` (`[RTOS-WDT-01]`) because it prevents `bspWatchdog_ReportHeartbeat` from running when the RS-485 bus is idle
