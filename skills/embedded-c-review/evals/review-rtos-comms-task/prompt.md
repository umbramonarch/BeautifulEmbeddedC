---
tags: [embedded-c-review, rtos, isr]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Please review `comms_task.h` and `comms_task.c` for our RS-485 telemetry FreeRTOS task and UART
interrupt handler. We saw intermittent watchdog resets when the RS-485 bus goes quiet and hard
faults under heavy UART traffic. Write your review findings to `REVIEW.md`. Do not modify
`comms_task.h` or `comms_task.c`.

Input files: comms_task.h, comms_task.c
