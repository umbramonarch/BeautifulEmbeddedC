---
type: llm
focus: trace
weight: 1
---

`MCU-B`'s `EOT` and `OVR` status flags are cleared via direct Write-1-to-Clear assignment to `spi->IFCR` (`MCU_B_SPI_IFCR_EOTC_MASK` / `MCU_B_SPI_IFCR_OVRC_MASK`) rather than read-modify-write on `SR`
