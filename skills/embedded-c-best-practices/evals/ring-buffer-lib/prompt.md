---
tags: [embedded-c-best-practices]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Write a reusable Embedded C byte ring buffer library in `libs/ring_buf/ringBuf.h` and
`libs/ring_buf/ringBuf.c` for buffering UART and telemetry packets on a microcontroller, along
with a host GCC unit test in `libs/ring_buf/test/test_ring_buf.c`. It should support
initializing a ring buffer over a caller-provided byte array, pushing a single byte, popping a
single byte, querying current count and remaining free space, and resetting the buffer. Make
sure the unit test compiles and passes on host `gcc`.
