---
tags: [embedded-c-best-practices, rtos, watchdog]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Implement a rendezvous RTOS watchdog supervisor module in `src/app/appWatchdog.h` and
`src/app/appWatchdog.c`, along with a host unit test suite in `tests/test_appWatchdog.c`, using
the provided headers and link-time fake in `src/config/project_types.h`, `src/bsp/bspRtos.h`,
`src/bsp/bspWatchdog.h`, and `tests/fakes/fake_bspWatchdog.h` / `fake_bspWatchdog.c`:

1. **Monitored tasks & `.rodata` configuration table:**
   - Define `AppWatchdogTask_e` with `APP_WDT_TASK_CONTROL = 0`, `APP_WDT_TASK_COMMS`,
     `APP_WDT_TASK_THERMAL`, and `APP_WDT_TASK_COUNT`.
   - Define a `const` configuration table `kAppWatchdogConfigTable[APP_WDT_TASK_COUNT]` in
     `.rodata` paired with a compile-time `_Static_assert` matching `APP_WDT_TASK_COUNT`.
2. **OS-agnostic core & atomic heartbeat tracking:**
   - `MUST_CHECK Status_e appWatchdog_Init(void)`: initializes module state and calls
     `bspWatchdog_Init` with a `200 ms` hardware watchdog window.
   - `MUST_CHECK Status_e appWatchdog_ReportHeartbeat(AppWatchdogTask_e taskId)`: validates
      initialization and `taskId < APP_WDT_TASK_COUNT`, and sets the task's heartbeat bit inside
     a save/restore critical section (`bspRtos_EnterCritical()` / `bspRtos_ExitCritical()`).
   - `MUST_CHECK Status_e appWatchdog_SupervisorStep(void)`: atomically snapshots and clears
     the heartbeat bitmask. If **all** `APP_WDT_TASK_COUNT` tasks checked in, calls
     `bspWatchdog_Kick()` and returns `STATUS_OK`. If any task missed its check-in, does **not**
     kick the hardware watchdog, records the lowest-numbered missing task via
     `bspWatchdog_LatchFaultTask()`, and returns `STATUS_ERR_TIMEOUT`.
3. **Static RTOS task creation & Humble Task Wrapper:**
   - `MUST_CHECK Status_e appWatchdog_StartTaskStatic(void)`: registers the supervisor task
     using `bspRtos_TaskCreateStatic` backed by a `static` stack array and `static` TCB struct
     (zero dynamic heap allocation).
   - `void vWatchdogSupervisorTask(void *pvParameters)`: casts `(void)pvParameters;`, sleeps
     for a bounded `Milliseconds_t` period (`50 ms`, never an infinite delay) via
     `bspRtos_DelayMs`, and executes `appWatchdog_SupervisorStep()`.
4. **Host unit tests (`tests/test_appWatchdog.c`):**
   - Compile and run on host `gcc` (linking `src/app/appWatchdog.c`,
     `tests/fakes/fake_bspWatchdog.c`, and `tests/test_appWatchdog.c`) verifying: uninitialized
     and invalid task ID guards, normal all-tasks-checked-in kick behavior, single missing task
     starvation (verifying `bspWatchdog_Kick` is **not** called and the missing task ID is
     latched), and static task creation.
