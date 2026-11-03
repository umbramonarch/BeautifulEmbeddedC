---
type: llm
focus: trace
weight: 1
---

Chip-select (`CS`) assertion and deassertion in `drvSpi.c` use `MCU_B_GPIO_Ports[cfg->csPortId].BSRR` atomic bit set/reset writes (`MCU_B_GPIO_BSRR_RESET` / `MCU_B_GPIO_BSRR_SET`) and always deassert `CS` even when a transfer times out
