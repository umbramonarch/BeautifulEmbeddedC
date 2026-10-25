---
type: llm
focus: trace
weight: 1
---

`#include "vendor_mcu_hal.h"` and `VENDOR_TIM_Regs *` are removed from the public `motor_ctrl.h` header so the header is 100% vendor-free and host-compilable
