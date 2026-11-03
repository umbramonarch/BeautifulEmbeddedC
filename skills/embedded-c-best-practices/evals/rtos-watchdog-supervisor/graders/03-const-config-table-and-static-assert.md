---
type: llm
focus: trace
weight: 1
---

`kAppWatchdogConfigTable` is qualified `const` so it lands in `.rodata` Flash and is paired with a compile-time `_Static_assert` proving its length matches `APP_WDT_TASK_COUNT` (`[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]`)
