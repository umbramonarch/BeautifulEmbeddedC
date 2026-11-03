---
type: llm
focus: trace
weight: 1
---

Task creation in `appWatchdog_StartTaskStatic` uses `bspRtos_TaskCreateStatic` backed by file-scope `static` stack (`BspRtosStackWord_t`) and `static` TCB (`BspRtosStaticTcb_t`) buffers with zero calls to `malloc`, `calloc`, `free`, or dynamic `xTaskCreate` (`[RTOS-STATIC-01]`, `[JPL-3]`)
