---
type: llm
focus: trace
weight: 1
---

Fallible public functions return a `MUST_CHECK` (`__attribute__((warn_unused_result))`) status enum, and host unit tests compile and pass under `gcc -std=c11` without `#ifdef TEST` in production files
