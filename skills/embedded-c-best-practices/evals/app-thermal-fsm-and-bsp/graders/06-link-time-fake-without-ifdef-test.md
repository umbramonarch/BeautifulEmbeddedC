---
type: llm
focus: trace
weight: 1
---

Host unit testing uses link-time substitution (`fake_drvPwm.c` linked in place of `drvPwm.c`), and no `#ifdef TEST` or `#ifdef UNIT_TEST` conditional compilation appears in production `.c` or `.h` files
