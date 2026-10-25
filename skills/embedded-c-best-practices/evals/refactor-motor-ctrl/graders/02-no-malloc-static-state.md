---
type: llm
focus: trace
weight: 1
---

`malloc` and `<stdlib.h>` are removed; runtime state is stored in a `static` array or caller-supplied struct with zero dynamic memory allocation
