---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags that `g_motorConfig` is mutable in SRAM instead of `const` in `.rodata` Flash (and recommends `const` plus `_Static_assert`)
