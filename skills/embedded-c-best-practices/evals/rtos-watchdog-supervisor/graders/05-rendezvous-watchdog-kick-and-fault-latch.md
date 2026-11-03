---
type: llm
focus: trace
weight: 1
---

`appWatchdog_SupervisorStep` calls `bspWatchdog_Kick()` only when all `APP_WDT_TASK_COUNT` tasks have reported a heartbeat in the window, and when any task is missing it does not call `bspWatchdog_Kick()`, latches the missing task via `bspWatchdog_LatchFaultTask()`, and returns `STATUS_ERR_TIMEOUT` (`[RTOS-WDT-01]`)
