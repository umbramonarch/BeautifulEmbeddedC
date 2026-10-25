# Changelog

All notable changes to this project are listed here. Versions follow
[Semantic Versioning](https://semver.org/), and the version lives in
`.claude-plugin/plugin.json`.

## [Unreleased]

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

[Unreleased]: https://github.com/umbramonarch/BeautifulEmbeddedC/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/umbramonarch/BeautifulEmbeddedC/releases/tag/v1.0.0
