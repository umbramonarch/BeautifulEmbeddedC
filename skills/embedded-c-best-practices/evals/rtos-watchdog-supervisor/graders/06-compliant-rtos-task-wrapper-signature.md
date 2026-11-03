---
type: llm
focus: trace
weight: 1
---

`vWatchdogSupervisorTask` uses the standard RTOS task signature `void vWatchdogSupervisorTask(void *pvParameters)` with `(void)pvParameters;` and blocks for a finite `Milliseconds_t` window via `bspRtos_DelayMs` (`[RTOS-WDT-01]`)
