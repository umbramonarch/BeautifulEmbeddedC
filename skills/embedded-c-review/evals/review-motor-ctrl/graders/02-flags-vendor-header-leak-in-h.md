---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags that `motor_ctrl.h` leaks `#include "vendor_mcu_hal.h"` and `VENDOR_TIM_Regs *` into the public header, breaking layer isolation and host testability
