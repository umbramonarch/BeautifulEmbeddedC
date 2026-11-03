---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags using a binary semaphore (`xSemaphoreCreateBinary`) instead of a priority-inheriting mutex (`xSemaphoreCreateMutexStatic`) to lock the shared RS-485 bus across tasks (`[RTOS-MUTEX-01]`)
