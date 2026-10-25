---
type: llm
focus: trace
weight: 1
---

Public functions return an explicit status enum annotated with `__attribute__((warn_unused_result))` (or `MUST_CHECK`), and `motor_Update` checks the status of `motor_ReadCurrent` and `motor_SetSpeed`
