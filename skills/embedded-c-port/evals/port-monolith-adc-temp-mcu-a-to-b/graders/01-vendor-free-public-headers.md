---
type: llm
focus: trace
weight: 1
---

All public `.h` headers (including `ntc_monitor.h` or any layered `app`/`bsp`/`drv` headers) are 100% free of `#include "vendor_mcu_a_regs.h"`, `#include "vendor_mcu_b_hal.h"`, and hardware register pointer types
