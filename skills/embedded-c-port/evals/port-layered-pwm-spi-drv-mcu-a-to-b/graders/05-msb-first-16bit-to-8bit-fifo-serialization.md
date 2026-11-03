---
type: llm
focus: trace
weight: 1
---

`drvSpi_TransferWord` serializes the 16-bit `txWord` MSB-first across `MCU-B`'s 8-bit `TXDR8`/`RXDR8` byte FIFO (high byte `(txWord >> 8U) & 0xFFU` first, low byte `txWord & 0xFFU` second) and reassembles the 16-bit `*outRxWord`
