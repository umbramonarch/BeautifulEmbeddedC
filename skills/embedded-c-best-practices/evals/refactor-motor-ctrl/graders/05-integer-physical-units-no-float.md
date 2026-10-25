---
type: llm
focus: trace
weight: 1
---

All `float` types (`duty`, `max_current`, `amps`) and bare `int` types are replaced by `<stdint.h>` fixed-width integer types with explicit physical unit suffixes (`_ma`, `_hz`, `_permille`) and/or single-field unit wrapper structs (`Milliamps_t`, `DutyPermille_t`, `FreqHz_t`)
