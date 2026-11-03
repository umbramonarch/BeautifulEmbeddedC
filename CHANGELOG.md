# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/), and the version lives in
`.claude-plugin/plugin.json`.

## [Unreleased]

## [1.1.0] - 2026-11-03

### Added

- **`embedded-c-port` skill** (`skills/embedded-c-port/SKILL.md`) for porting firmware,
  peripheral drivers, and board support packages across microcontroller vendors, instruction-set
  architectures (8/16-bit to 32-bit, AVR/MSP/PIC to Cortex-M or RISC-V), and vendor HAL/register
  SDKs into deterministic, vendor-neutral, host-testable C11. Each port separates the physical
  domain contract (millivolts, hertz, permille, milliseconds) from the target silicon mechanics
  (clock trees, ADC resolution, bus ratios, interrupt-flag semantics). Backed by two graded
  cross-MCU evaluation suites (`port-monolith-adc-temp-mcu-a-to-b` and
  `port-layered-pwm-spi-drv-mcu-a-to-b`) totaling 24 binary graders.
- **RTOS & ISR framework support**
  (`skills/embedded-c-best-practices/references/rtos-and-isr-frameworks.md`): the sixth
  authoritative digest, covering framework conventions to leave alone (`void vTask(void
  *pvParameters)`, `for (;;)` task superloops, hardware vector handler names) and RTOS
  concurrency rules (`[RTOS-STATIC-01]`, `[RTOS-ISR-01]`, `[RTOS-MUTEX-01]`, `[RTOS-WDT-01]`,
  `[RTOS-SEAM-01]`). Pairs with two new graded RTOS evaluation suites
  (`review-rtos-comms-task` and `rtos-watchdog-supervisor`) totaling 22 binary graders.
- **Expanded `lints/check_arch.py` and new `lints/CMakeLists.txt`:** seven new static checks
  (`[BARR-NO-BITFIELDS]`, `[BARR-8.3.b]`, `[BARR-ISR-ATOMIC]`, `[RTOS-STATIC-01]`,
  `[RTOS-ISR-01]`, `[RTOS-WDT-01]`, `[RTOS-SEAM-01]`) plus an extended `[JPL-1]` that now bans
  `alloca` and direct recursion alongside `goto`, `setjmp`, and `longjmp`; a drop-in
  dual-target `lints/CMakeLists.txt` with per-layer include isolation and CTest host unit
  tests; and `clang-format`-clean generated templates in `lints/scaffold.py`.
- **CI and self-verification suite** (`scripts/`, `lints/check/`, `tests/`,
  `.github/workflows/check.yml`, `CONTRIBUTING.md`):
  - `scripts/check-skill.py` validates plugin manifests, changelog links, every relative link,
    skill frontmatter, rule-ID provenance, and eval case structure, backed by 59 unit tests in
    `tests/test_check_skill.py`.
  - `scripts/check-examples.py` with `scripts/examples.json` compiles every C11 code snippet
    across the skills, reference digests, `README.md`, and `examples/` under the strict
    `-Werror` flag set.
  - `lints/check/` deliberate-violation fixtures with `scripts/check-lints.py` prove every
    `check_arch.py` rule fires on its exact line and verify the full `scaffold.py` round-trip.

### Changed

- Four pre-existing evaluation suites (`ring-buffer-lib`, `app-thermal-fsm-and-bsp`,
  `refactor-motor-ctrl`, `review-motor-ctrl`) now run alongside the four new suites, for eight
  graded suites and 88 binary graders in total.
- The plugin description, marketplace description, and `keywords` now advertise all three
  skills, all six reference digests, the CMake and Make build configs, and multi-layer
  scaffolding.

## [1.0.0] - 2026-10-25

### Added

- `embedded-c-best-practices` writing skill (`skills/embedded-c-best-practices/SKILL.md`)
  covering all Embedded C firmware layers (`app`, `bsp`, `config`, `drv`, `libs`, ISRs, and
  host unit tests), backed by five on-demand authority digests in `references/`:
  - `beningo-reusable-firmware.md` (Jacob Beningo, *Reusable Firmware Development*)
  - `grenning-embedded-tdd.md` (James Grenning, *Test-Driven Development for Embedded C*)
  - `nasa-jpl-power-of-10.md` (Gerard Holzmann, *NASA JPL Power of 10*)
  - `barr-c-coding-standard.md` (Michael Barr, *BARR-C:2018 Embedded C Coding Standard*)
  - `misra-and-type-safety.md` (MISRA C Essential Type Model & Zero-Cost C11 Type Safety)
- `embedded-c-review` code review skill (`skills/embedded-c-review/SKILL.md`) with a
  prioritized 3-tier report template (`Must fix`, `Should fix`, `Consider`, and
  `What's already good`) and an unedited sample review (`examples/review-motor-ctrl.md`).
- Drop-in lint and scaffolding suite in `lints/`:
  - `.clang-format` (mandatory braces via `InsertBraces: true`, 100-column limit, no
    single-line control statements)
  - `.clang-tidy` (`bugprone-*`, `cert-*`, `readability-*`, <= 60-line function checks, and
    naming rules)
  - `.clangd` (cross-compiler flag filtering and strict include diagnostics)
  - `Makefile` (dual-target cross-compilation with per-layer `-I` isolation + host `gcc` unit
    test runner + `format`, `tidy`, and `arch` gates)
  - `check_arch.py` (zero-dependency Python 3 checker enforcing universal C11 safety rules on
    every `.c`/`.h` file and layer dependency boundaries across `app`, `bsp`, `config`,
    `drv`, and `libs`)
  - `scaffold.py` (all-layer generator supporting `--init-project` and
    `--layer {app,bsp,config,drv,lib}`)
- Four graded evaluation suites totaling 42 binary graders across both skills
  (`ring-buffer-lib`, `app-thermal-fsm-and-bsp`, `refactor-motor-ctrl`, and
  `review-motor-ctrl`).

[Unreleased]: https://github.com/umbramonarch/BeautifulEmbeddedC/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/umbramonarch/BeautifulEmbeddedC/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/umbramonarch/BeautifulEmbeddedC/releases/tag/v1.0.0
