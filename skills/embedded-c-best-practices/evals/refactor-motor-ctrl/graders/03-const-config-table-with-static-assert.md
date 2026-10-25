---
type: llm
focus: trace
weight: 1
---

The motor configuration table is qualified `const` (so it resides in `.rodata` Flash) and paired with a `_Static_assert` verifying its element count matches a channel enum count
