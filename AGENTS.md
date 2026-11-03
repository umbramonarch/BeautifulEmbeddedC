# Repository Guidelines

## Project Structure & Module Organization

`BeautifulEmbeddedC` is a standalone Agent Skills repository and Claude Code plugin for writing, reviewing, porting, and enforcing safety-critical Embedded C (C11) across all firmware layers.

- `.claude-plugin/`: Plugin (`plugin.json`) and self-hosted marketplace (`marketplace.json`) manifests.
- `skills/embedded-c-best-practices/`: Writing skill (`SKILL.md`), six authoritative digests (`references/*.md`, including `rtos-and-isr-frameworks.md`), and writing evaluations (`evals/`).
- `skills/embedded-c-review/`: Code review skill (`SKILL.md`) and review evaluations (`evals/`).
- `skills/embedded-c-port/`: Cross-MCU porting skill (`SKILL.md`) for moving firmware, drivers, and BSPs between microcontroller vendors, instruction-set architectures, and vendor SDKs, plus porting evaluations (`evals/`).
- `lints/`: Drop-in enforcement and scaffolding files for Embedded C projects (`.clang-format`, `.clang-tidy`, `.clangd`, `Makefile`, `CMakeLists.txt`, `check_arch.py`, `scaffold.py`) and `lints/check/`, the deliberate-violation fixtures that prove every architecture rule fires.
- `scripts/`: Repository self-verification gates (`check-skill.py`, `check-lints.py`, `check-examples.py`, `examples.json`).
- `tests/`: Unit tests for the verification scripts (`test_check_skill.py`).
- `examples/`: Reference outputs such as `examples/review-motor-ctrl.md`.
- `.github/workflows/check.yml`: CI that runs all gates on every push and pull request.

## Build, Test, and Development Commands

- `python3 lints/scaffold.py --init-project --root <dir>`: Scaffold a complete 4-layer (`app`, `bsp`, `config`, `drv`) + vertical `libs/` Embedded C project structure in `<dir>`.
- `python3 lints/scaffold.py --layer <app|bsp|config|drv|lib> <name> --root <dir>`: Scaffold a compliant module and host unit test in any layer.
- `python3 lints/check_arch.py <dir>`: Validate C11 safety invariants, RTOS concurrency rules, file section banners, and layer include boundaries across all `.c` and `.h` files.
- `python3 scripts/check-skill.py`: Validate plugin manifests, `CHANGELOG.md` release links, every relative link in `README.md`/`CONTRIBUTING.md`, skill frontmatter, rule-ID provenance, and eval case structure.
- `python3 scripts/check-lints.py`: Run `check_arch.py` against the `lints/check/` violation fixtures (asserting every rule fires on its exact line) and verify the full `scaffold.py` round-trip is clean and compiles.
- `python3 scripts/check-examples.py`: Compile every C11 code snippet in the skills, reference digests, `README.md`, and `examples/` under the strict warning flags.
- `python3 -m unittest discover -s tests`: Run the verification-script unit tests.
- `claude plugin validate .`: Validate plugin manifests and skill frontmatter.
- `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`: Run graded evaluations from inside a skill directory.

## Coding Style & Naming Conventions

- **Markdown (`SKILL.md`, `references/*.md`, `README.md`)**: Wrap lines at ~95 columns. Start rule bullets with a bold imperative sentence followed by the concrete failure mode it prevents. Keep everything 100% vendor-neutral.
- **Embedded C Examples & Templates**: Follow C11 (`-std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wsign-conversion`). Use `module_ActionNoun()` for public APIs, `static` for private helpers, `ModuleConfig_t` for types, physical unit suffixes (`_mv`, `_ma`, `_hz`, `_ms`), and mandatory braces on all control blocks.
- **Python Scripts (`lints/*.py`, `scripts/*.py`)**: Python 3.9+ standard library only (zero external `pip` dependencies).

## Testing Guidelines

- Every code snippet in `SKILL.md` and `references/*.md` must be valid, warning-free C11; `python3 scripts/check-examples.py` compiles them all from `scripts/examples.json`.
- Test changes to `lints/scaffold.py` and `lints/check_arch.py` with `python3 scripts/check-lints.py`, which scaffolds a sample multi-layer project in a temporary directory, runs `check_arch.py`, and compiles host tests with `gcc`. Add a `// expect: [RULE-ID]` fixture under `lints/check/` whenever a new architecture rule is introduced.
- Run `python3 scripts/check-skill.py` and `python3 -m unittest discover -s tests` after editing manifests, skills, `README.md`, or `CONTRIBUTING.md`.
- Grader files in `skills/*/evals/<case>/graders/NN-*.md` must contain a single binary, falsifiable assertion sentence.

## Commit & Pull Request Guidelines

- **Never commit, edit, or push directly to `main`.** Always create and work on a feature or fix branch (e.g., `feat/<topic>` or `fix/<topic>`) and merge via Pull Request.
- Use imperative, concise commit subjects (e.g., `Add NASA JPL Power of 10 reference digest`).
- Bump `version` in `.claude-plugin/plugin.json` and document changes in `CHANGELOG.md` when updating skills or lints.
- PRs must keep all skills and tools 100% vendor-neutral and verify that `check_arch.py`, host GCC checks, `scripts/check-skill.py`, `scripts/check-lints.py`, and `scripts/check-examples.py` all pass.
