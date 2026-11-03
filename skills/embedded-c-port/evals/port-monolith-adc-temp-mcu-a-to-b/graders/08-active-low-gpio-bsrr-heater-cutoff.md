---
type: llm
focus: trace
weight: 1
---

Heater cutoff control on `MCU-B` accounts for the active-low `PB4` wiring using atomic `MCU_B_GPIOB->BSRR` set/reset writes (driving `PB4` low via bits `[31:16]` when cutoff is asserted and high via bits `[15:0]` when deasserted)
