---
type: llm
focus: trace
weight: 1
---

`drvSpi_Init` computes the `MCU-B` `CFG1.MBR` baud-rate divider against `MCU_B_SPI_PCLK_HZ` (`96000000U`) so that `96 MHz / 16 = 6 MHz` (`mbr = 3U`) is selected for a `6000000 Hz` maximum clock
