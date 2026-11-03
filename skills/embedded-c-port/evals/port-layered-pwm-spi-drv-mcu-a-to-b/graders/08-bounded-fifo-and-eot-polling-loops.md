---
type: llm
focus: trace
weight: 1
---

Every hardware status polling loop in `drvSpi.c` (`TXP`, `RXP`, and `EOT`) has an explicit cycle bound and returns `STATUS_ERR_TIMEOUT` on expiry
