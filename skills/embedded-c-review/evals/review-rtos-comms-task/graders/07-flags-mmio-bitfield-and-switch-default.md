---
type: llm
focus: trace
weight: 1
---

`REVIEW.md` flags mapping the hardware status register with the C bit-field struct `UsartSrReg_t` (`[BARR-NO-BITFIELDS]`) and the `switch (frame->cmd)` block missing a `default:` branch (`[BARR-8.3.b]` / `[MISRA-16.4]`)
