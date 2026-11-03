---
type: llm
focus: trace
weight: 1
---

`appWatchdog_ReportHeartbeat` and `appWatchdog_SupervisorStep` guard updates and snapshots of the shared heartbeat bitmask using `bspRtos_EnterCritical()` and `bspRtos_ExitCritical()` save/restore critical sections (`[BARR-ISR-ATOMIC]`)
