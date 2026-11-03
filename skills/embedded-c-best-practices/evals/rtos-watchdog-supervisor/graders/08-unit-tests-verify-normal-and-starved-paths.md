---
type: llm
focus: trace
weight: 1
---

`tests/test_appWatchdog.c` tests both the all-tasks-healthy path (verifying `fakeBspWatchdog_GetKickCount()` increments) and the starved-task path (verifying `fakeBspWatchdog_GetKickCount()` does not increment and `fakeBspWatchdog_GetLatchedFaultTask()` records the missing task ID) with zero `#ifdef TEST` blocks in production files (`[GRENNING-SEAM-01]`)
