---
type: llm
focus: trace
weight: 1
---

`tests/test_appDacCtrl.c` compiles and passes unchanged on host `gcc` via `fake_drvSpi.c`, and host unit tests also verify `drvSpi.c` against `MCU_B_SPI1` registers
