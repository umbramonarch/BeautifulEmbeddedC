# CLAUDE.md

@AGENTS.md

## Repository Overview

`BeautifulEmbeddedC` teaches coding agents to write, review, and enforce deterministic, testable, safety-critical Embedded C (C11) across **all types of C files** (`app`, `bsp`, `config`, `drv`, `libs`, ISRs, and host unit tests).

It consists of:
1. **`skills/embedded-c-best-practices/`**: The writing skill (`SKILL.md`) backed by five on-demand authority digests in `references/` (`beningo-reusable-firmware.md`, `grenning-embedded-tdd.md`, `nasa-jpl-power-of-10.md`, `barr-c-coding-standard.md`, `misra-and-type-safety.md`) and three graded evaluation suites in `evals/`.
2. **`skills/embedded-c-review/`**: The code review skill (`SKILL.md`) and its graded evaluation suite in `evals/review-motor-ctrl/`, paired with a full sample output in `examples/review-motor-ctrl.md`.
3. **`lints/`**: Drop-in `.clang-format`, `.clang-tidy`, `.clangd`, dual-target `Makefile`, `check_arch.py` (universal C11 safety + layer boundary checker), and `scaffold.py` (all-layer project and module generator).

## Maintaining Synchronization Across Pillars

- **Branch workflow:** Never edit, commit, or push directly on `main`. Always switch to a dedicated feature branch (`feat/<topic>` or `fix/<topic>`) before making any changes.
- Whenever you add or modify a rule in `skills/embedded-c-best-practices/SKILL.md`, ensure its rule code (e.g. `[BENINGO-CFG-CONST]`, `[JPL-2]`, `[BARR-1.3.a]`, `[MISRA-10.3]`, `[GRENNING-SEAM]`) matches the corresponding digest in `skills/embedded-c-best-practices/references/*.md`, the review priorities in `skills/embedded-c-review/SKILL.md`, and the automated checks in `lints/check_arch.py` and `lints/.clang-tidy`.
- Keep all skills, references, lints, and examples 100% vendor-neutral (never hardcode a specific vendor SDK or proprietary project name).
