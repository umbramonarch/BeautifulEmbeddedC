# CLAUDE.md

@AGENTS.md

## Repository Overview

`BeautifulEmbeddedC` teaches coding agents to write, review, port, and enforce deterministic, testable, safety-critical Embedded C (C11) across **all types of C files** (`app`, `bsp`, `config`, `drv`, `libs`, ISRs, RTOS tasks, and host unit tests).

It consists of:

1. **`skills/embedded-c-best-practices/`**: The writing skill (`SKILL.md`) backed by six on-demand authority digests in `references/` (`beningo-reusable-firmware.md`, `grenning-embedded-tdd.md`, `nasa-jpl-power-of-10.md`, `barr-c-coding-standard.md`, `misra-and-type-safety.md`, `rtos-and-isr-frameworks.md`) and four graded evaluation suites in `evals/` (`ring-buffer-lib`, `app-thermal-fsm-and-bsp`, `refactor-motor-ctrl`, `rtos-watchdog-supervisor`).
2. **`skills/embedded-c-review/`**: The code review skill (`SKILL.md`) and its two graded evaluation suites (`evals/review-motor-ctrl/`, `evals/review-rtos-comms-task/`), paired with a full sample output in `examples/review-motor-ctrl.md`.
3. **`skills/embedded-c-port/`**: The cross-MCU porting skill (`SKILL.md`) for moving firmware, drivers, and BSPs between microcontroller vendors, instruction-set architectures, and vendor HAL/register SDKs, with two graded evaluation suites in `evals/` (`port-monolith-adc-temp-mcu-a-to-b`, `port-layered-pwm-spi-drv-mcu-a-to-b`).
4. **`lints/`**: Drop-in `.clang-format`, `.clang-tidy`, `.clangd`, dual-target `Makefile` and `CMakeLists.txt`, `check_arch.py` (universal C11 safety + RTOS concurrency + layer boundary checker), `scaffold.py` (all-layer project and module generator), and `lints/check/` (deliberate-violation fixtures proving every `check_arch.py` rule fires).
5. **`scripts/`**: Repository self-verification gates — `check-skill.py` (manifests, changelog links, skill frontmatter, relative links, rule-ID provenance, eval case structure), `check-lints.py` (runs `lints/check/` fixtures and the `scaffold.py` round-trip), and `check-examples.py` + `examples.json` (compiles every C11 snippet in the skills, digests, README, and examples).

## Maintaining Synchronization Across Pillars

- **Branch workflow:** Never edit, commit, or push directly on `main`. Always switch to a dedicated feature branch (`feat/<topic>` or `fix/<topic>`) before making any changes.
- Whenever you add or modify a rule in `skills/embedded-c-best-practices/SKILL.md`, ensure its rule code (e.g. `[BENINGO-CFG-CONST]`, `[JPL-2]`, `[BARR-1.3.a]`, `[MISRA-10.3]`, `[GRENNING-SEAM-01]`, `[RTOS-STATIC-01]`) matches the corresponding digest in `skills/embedded-c-best-practices/references/*.md`, the review priorities in `skills/embedded-c-review/SKILL.md`, the porting guidance in `skills/embedded-c-port/SKILL.md`, and the automated checks in `lints/check_arch.py` and `lints/.clang-tidy`.
- When a rule gains an automated check, add a deliberate-violation fixture to `lints/check/` so `scripts/check-lints.py` proves the rule fires, and keep `python3 scripts/check-skill.py`, `python3 scripts/check-examples.py`, and `python3 -m unittest discover -s tests` green.
- Keep all skills, references, lints, and examples 100% vendor-neutral (never hardcode a specific vendor SDK or proprietary project name).
