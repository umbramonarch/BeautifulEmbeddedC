---
type: llm
focus: trace
weight: 1
---

Public fallible functions (`appWatchdog_Init`, `appWatchdog_ReportHeartbeat`, `appWatchdog_SupervisorStep`, `appWatchdog_StartTaskStatic`) are annotated `MUST_CHECK`, return `Status_e`, and validate initialization state and `taskId < APP_WDT_TASK_COUNT` before mutating state (`[JPL-5]`, `[JPL-7]`, `[MISRA-17.7]`)
