---
tags: [embedded-c-best-practices]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Refactor `motor_ctrl.h` and `motor_ctrl.c` so they are safe for production embedded firmware
and testable on host `gcc`. Keep the same core capabilities (initializing two motor channels,
setting PWM duty, reading motor current, shutting down on overcurrent, and tracking overcurrent
faults), but fix all architectural, memory, loop-bound, type-safety, and ISR concurrency
defects. Document every change and any public signature updates in `CHANGES.md`.

Input files: motor_ctrl.h, motor_ctrl.c
