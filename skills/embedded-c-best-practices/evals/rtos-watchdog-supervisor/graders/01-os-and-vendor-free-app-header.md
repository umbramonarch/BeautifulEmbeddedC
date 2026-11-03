---
type: llm
focus: trace
weight: 1
---

`src/app/appWatchdog.h` and `src/app/appWatchdog.c` do not `#include` `FreeRTOS.h`, `task.h`, `queue.h`, or any vendor SDK header, depending only on standard C headers, `project_types.h`, `bspRtos.h`, and `bspWatchdog.h` (`[RTOS-SEAM-01]`, `[BENINGO-HDR-01]`)
