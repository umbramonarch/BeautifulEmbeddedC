---
type: llm
focus: trace
weight: 1
---

All `float` and `double` types and literals are removed from production code and replaced with fixed-width `<stdint.h>` integer physical units (such as millivolts `_mv` and deci-degrees Celsius `_deci_c` or single-field unit wrapper structs)
