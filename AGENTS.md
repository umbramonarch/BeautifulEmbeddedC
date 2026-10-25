# Repository Guidelines

## Project Structure & Module Organization

`BeautifulEmbeddedC` is a standalone Agent Skills repository and Claude Code plugin for writing, reviewing, and enforcing safety-critical Embedded C (C11) across all firmware layers.

- `.claude-plugin/`: Plugin (`plugin.json`) and self-hosted marketplace (`marketplace.json`) manifests.
- `skills/embedded-c-best-practices/`: Writing skill (`SKILL.md`), five authoritative digests (`references/*.md`), and writing evaluations (`evals/`).
- `skills/embedded-c-review/`: Code review skill (`SKILL.md`) and review evaluations (`evals/`).
- `lints/`: Drop-in enforcement and scaffolding files for Embedded C projects (`.clang-format`, `.clang-tidy`, `.clangd`, `Makefile`, `check_arch.py`, `scaffold.py`).
- `examples/`: Reference outputs such as `examples/review-motor-ctrl.md`.

## Build, Test, and Development Commands

- `python3 lints/scaffold.py --init-project --root <dir>`: Scaffold a complete 4-layer (`app`, `bsp`, `config`, `drv`) + vertical `libs/` Embedded C project structure in `<dir>`.
- `python3 lints/scaffold.py --layer <app|bsp|config|drv|lib> <name> --root <dir>`: Scaffold a compliant module and host unit test in any layer.
- `python3 lints/check_arch.py <dir>`: Validate C11 safety invariants, file section banners, and layer include boundaries across all `.c` and `.h` files.
- `claude plugin validate .`: Validate plugin manifests and skill frontmatter.
- `claude plugin eval . --allow-tools Write,Edit,Bash --scaffold`: Run graded evaluations from inside a skill directory.

## Coding Style & Naming Conventions

- **Markdown (`SKILL.md`, `references/*.md`, `README.md`)**: Wrap lines at ~95 columns. Start rule bullets with a bold imperative sentence followed by the concrete failure mode it prevents. Keep everything 100% vendor-neutral.
- **Embedded C Examples & Templates**: Follow C11 (`-std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wsign-conversion`). Use `module_ActionNoun()` for public APIs, `static` for private helpers, `ModuleConfig_t` for types, physical unit suffixes (`_mv`, `_ma`, `_hz`, `_ms`), and mandatory braces on all control blocks.
- **Python Scripts (`lints/*.py`)**: Python 3.9+ standard library only (zero external `pip` dependencies).

## Testing Guidelines

- Every code snippet in `SKILL.md` and `references/*.md` must be valid, warning-free C11.
- Test changes to `lints/scaffold.py` and `lints/check_arch.py` by scaffolding a sample multi-layer project in a temporary directory, running `check_arch.py`, and compiling host tests with `gcc`.
- Grader files in `skills/*/evals/<case>/graders/NN-*.md` must contain a single binary, falsifiable assertion sentence.

## Commit & Pull Request Guidelines

- **Never commit, edit, or push directly to `main`.** Always create and work on a feature or fix branch (e.g., `feat/<topic>` or `fix/<topic>`) and merge via Pull Request.
- Use imperative, concise commit subjects (e.g., `Add NASA JPL Power of 10 reference digest`).
- Bump `version` in `.claude-plugin/plugin.json` and document changes in `CHANGELOG.md` when updating skills or lints.
- PRs must keep all skills and tools 100% vendor-neutral and verify that `check_arch.py` and host GCC checks pass.
