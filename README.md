# Beautiful Embedded C

Three [Agent Skills](https://agentskills.io) and a drop-in lint/scaffolding suite for writing,
reviewing, porting, and enforcing deterministic, safety-critical Embedded C (C11) across **all
firmware layers** (`app`, `bsp`, `config`, `drv`, `libs`, ISRs, RTOS tasks, and host unit
tests):

- **`embedded-c-best-practices`** guides an agent while it writes or refactors any Embedded C
  file — application state machines, board support packages, product configuration headers,
  peripheral drivers, pure algorithmic libraries, interrupt service routines, RTOS tasks, or
  host unit tests.
- **`embedded-c-review`** audits existing `.c` and `.h` files, modules, or pull requests and
  produces a prioritized report (`Must fix` / `Should fix` / `Consider` / `What's already
  good`) where every finding cites `file:line`, the rule it violates, and the smallest code
  change that fixes it.
- **`embedded-c-port`** moves firmware, peripheral drivers, and board support packages from one
  microcontroller to another — across vendors, instruction-set architectures (8/16-bit to
  32-bit, AVR/MSP/PIC to Cortex-M or RISC-V), and vendor HAL/register SDKs — while preserving
  timing, scaling math, interrupt atomicity, and error recovery, and leaving a `PORTING.md`
  migration record behind.
- **`lints/`** is a drop-in enforcement and scaffolding directory (`.clang-format`,
  `.clang-tidy`, `.clangd`, dual-target `Makefile` and `CMakeLists.txt`, `check_arch.py`, and
  `scaffold.py`) that makes the compiler and build fail on every rule a machine can check.

They work with Claude Code, Factory Droid, OpenAI Codex, GitHub Copilot, Cursor, Gemini CLI,
and any other agent that reads the Agent Skills format. Every C code example in the skills
compiles cleanly under `gcc -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion
-Wsign-conversion`.

The skills are distilled from six industry-standard Embedded C authorities:

- [Jacob Beningo — *Reusable Firmware Development*](https://doi.org/10.1007/978-1-4842-3297-2)
  (4-layer horizontal architecture + pure vertical `libs/`, `const` configuration tables in
  `.rodata` Flash, vendor-free public headers, standardized Doxygen file banners)
- [James Grenning — *Test-Driven Development for Embedded C*](https://pragprog.com/titles/jgade/test-driven-development-for-embedded-c/)
  (dual-target host/target compilation, link-time substitution with fakes and spies without
  `#ifdef TEST` clutter, Humble Object pattern, opaque handles)
- [Gerard Holzmann — *NASA JPL Power of 10*](https://doi.org/10.1109/MC.2006.212) (simple
  control flow, fixed upper bounds on all hardware polling loops, zero dynamic allocation,
  functions <= 60 lines with assertions, zero warnings at maximum pedantic compiler settings)
- [Michael Barr — *BARR-C:2018 Embedded C Coding Standard*](https://barrgroup.com/embedded-systems/books/embedded-c-coding-standard)
  (module-prefixed naming, physical unit suffixes `_mv`/`_ma`/`_hz`/`_ms`, fixed-width
  `<stdint.h>` types, mandatory braces, `const`/`volatile` discipline, minimal atomic ISRs)
- [MISRA C Essential Type Model & Zero-Cost C11 Type Safety](https://www.misra.org.uk/)
  (single-field struct wrappers for physical units passed in registers at zero runtime cost,
  compile-time `_Static_assert` table proofs, `__attribute__((warn_unused_result))` status
  enums, zero implicit sign or float conversions)
- [RTOS & ISR framework conventions](skills/embedded-c-best-practices/references/rtos-and-isr-frameworks.md)
  (framework idioms to leave alone — `void vTask(void *pvParameters)`, `for (;;)` task
  superloops, hardware vector handler names — plus static RTOS object allocation, ISR-safe
  deferred processing, priority-inheriting mutexes over binary semaphores, bounded blocking
  with watchdog liveness, and an OS-agnostic state machine core)

Where the sources disagree, the skill picks a side and states why. Each source also has a
condensed digest in `skills/embedded-c-best-practices/references/` that the agent loads on
demand when a task needs deeper detail.

## What it changes

Asked to write a thermal protection module and PWM fan controller, an agent without the skill
typically leaks vendor SDK headers into public `.h` files, puts mutable configuration structs
in SRAM, uses raw `int` or `float` for millivolts and duty cycle, writes unbounded hardware
polling loops (`while (!(ADC_SR & READY));`), and leaves no seam for host unit testing:

```c
// Without the skill
#include "vendor_mcu_hal.h"   // leaked into public header; breaks host gcc builds

typedef struct {
    int channel;
    float max_temp;           // soft-float bloat + precision hazards
} ThermalCfg;

ThermalCfg g_cfg = { 0, 85.0f }; // mutable: wastes SRAM instead of .rodata Flash

void thermal_update(void) {
    while (!(ADC1->SR & 1));  // unbounded loop: hangs forever if clock/ADC faults
    int raw = ADC1->DR;
    if (raw > 3100)
        PWM_SetDuty(100);     // unbraced body, raw magic numbers, ignored status
}
```

```c
// With the skill
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "project_types.h"    // vendor-free types: Millivolts_t, DutyPermille_t, Status_e

typedef struct {
    Millivolts_t tripThreshold_mv;
    Millivolts_t hysteresis_mv;
    DutyPermille_t failSafeDuty_permille;
} AppThermalConfig_t;

MUST_CHECK Status_e appThermal_Init(const AppThermalConfig_t * const config);
MUST_CHECK Status_e appThermal_Step(Millivolts_t sensorReading_mv,
                                    DutyPermille_t * const outDuty_permille);
```

## Install

### Any agent, one command

If you use the [`skills`](https://www.npmjs.com/package/skills) CLI, install into Claude Code,
Codex, Copilot, Cursor, Gemini CLI, or any other supported agent with:

```bash
npx skills add umbramonarch/BeautifulEmbeddedC
```

### Claude Code

From your shell:

```bash
claude plugin marketplace add umbramonarch/BeautifulEmbeddedC
claude plugin install beautiful-embedded-c@beautiful-embedded-c
```

Or inside a Claude Code session:

```text
/plugin marketplace add umbramonarch/BeautifulEmbeddedC
/plugin install beautiful-embedded-c@beautiful-embedded-c
```

### GitHub Copilot

```bash
gh skill install umbramonarch/BeautifulEmbeddedC embedded-c-best-practices
gh skill install umbramonarch/BeautifulEmbeddedC embedded-c-review
gh skill install umbramonarch/BeautifulEmbeddedC embedded-c-port
```

### Gemini CLI

```bash
gemini skills install https://github.com/umbramonarch/BeautifulEmbeddedC.git --path skills/embedded-c-best-practices
gemini skills install https://github.com/umbramonarch/BeautifulEmbeddedC.git --path skills/embedded-c-review
gemini skills install https://github.com/umbramonarch/BeautifulEmbeddedC.git --path skills/embedded-c-port
```

### Factory Droid, OpenAI Codex, Cursor, or anything else: copy the folder

Clone the repository and copy all three skill directories into the path your agent reads:

```bash
git clone https://github.com/umbramonarch/BeautifulEmbeddedC.git
```

| Agent | User-wide skills directory | Project skills directory |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Factory Droid | `~/.factory/skills/` | `.factory/skills/` |
| OpenAI Codex | `~/.agents/skills/` | `.agents/skills/` |
| GitHub Copilot | `~/.copilot/skills/` | `.github/skills/` |
| Cursor | `~/.cursor/skills/` | `.cursor/skills/` |
| Gemini CLI | `~/.gemini/skills/` | `.gemini/skills/` |

### claude.ai

Zip a skill folder (excluding `evals/`) and upload it in **Settings -> Capabilities -> Skills**:

```bash
cd skills && zip -r embedded-c-best-practices.zip embedded-c-best-practices -x '*/evals/*'
cd skills && zip -r embedded-c-review.zip embedded-c-review -x '*/evals/*'
cd skills && zip -r embedded-c-port.zip embedded-c-port -x '*/evals/*'
```

## Reviewing existing code

Ask your agent to review any `.c` or `.h` file, layer (`src/app/`, `src/bsp/`, `src/config/`,
`drvs/`, `libs/`), or pull request:

```text
Review src/app/appThermal.c and drvs/pwm/drvPwm.c before we merge.
```

The `embedded-c-review` skill runs `clang-format`, `clang-tidy`, `check_arch.py`, and host
tests when available, then produces a report grouped into **Must fix**, **Should fix**,
**Consider**, and **What's already good**. Every finding cites `file:line`, the rule ID and
source authority, and a minimal C diff. See [`examples/review-motor-ctrl.md`](examples/review-motor-ctrl.md)
for a complete, unedited review report produced by the skill.

## Porting across microcontrollers

Ask your agent to move firmware from one MCU to another, or to replace direct register/HAL
calls with a portable layer split:

```text
Port drvs/spi/drvSpi.c from the MCU-A SDK to the MCU-B SDK without touching src/app/.
```

The `embedded-c-port` skill separates the **physical domain contract** (millivolts, hertz,
permille, milliseconds) from the **silicon mechanics** (register layout, clock trees,
peripheral bus ratios, ADC resolution and reference voltage, interrupt-flag clear semantics,
GPIO active level). It inventories the source module before editing, retargets only the layer
that owns the silicon, keeps `src/app/` and public headers diff-free, re-derives every baud
rate, prescaler, and timeout counter for the target clock tree, and records the mapping and
scaling tables in a `PORTING.md` migration record so the next port starts from facts. It also
catches the classic cross-MCU bugs: `|=`/`&=` written to a write-1-to-clear status register,
10-bit/5.0 V scaling carried onto a 12-bit/3.3 V ADC, and blocking OS calls left inside an
interrupt vector.

## Enforcing the rules and scaffolding projects (`lints/`)

Prose guidelines get forgotten under context pressure; compiler flags and fast static checks
do not. Copy the files from `lints/` into your firmware repository root — pick the `Makefile`
or the equivalent `CMakeLists.txt` (both enforce strict per-layer include-path isolation so
upper layers physically cannot include a lower layer or vendor SDK header) — or scaffold a
fresh multi-layer project in one command:

```bash
# Scaffold a complete 4-layer (app, bsp, config, drv) + vertical libs/ project
python3 lints/scaffold.py --init-project --root /path/to/firmware

# Scaffold a new module + host unit test in any layer
python3 lints/scaffold.py --layer app thermal --root /path/to/firmware
python3 lints/scaffold.py --layer config thermal --root /path/to/firmware
python3 lints/scaffold.py --layer bsp pwm --root /path/to/firmware
python3 lints/scaffold.py --layer drv pwm --root /path/to/firmware
python3 lints/scaffold.py --layer lib ring_buf --root /path/to/firmware

# Run the architecture & C11 safety gate (~0.1s) across all .c and .h files
python3 lints/check_arch.py /path/to/firmware

# CMake alternative to the Makefile: host unit tests via CTest + the same arch gate
cmake -B build && cmake --build build --target arch && ctest --test-dir build --output-on-failure
```

`check_arch.py` covers the layer boundaries plus universal C11 safety and RTOS concurrency
rules — banned `goto`/`setjmp`/`alloca`/recursion, unbounded hardware polling loops, dynamic
allocation, floating point in firmware, struct bit-fields, `switch` without a `default`,
unconditional interrupt enables, dynamic RTOS object creation, `portMAX_DELAY` blocking, and
blocking OS calls inside interrupt vectors.

The suite verifies itself: `python3 scripts/check-lints.py` runs `check_arch.py` against the
deliberate-violation fixtures in `lints/check/` and asserts every rule fires on its exact line,
then proves the `scaffold.py` round-trip is `clang-format` clean, `check_arch.py` clean, and
compiles under `gcc`.

## What the writing skill covers

`skills/embedded-c-best-practices/SKILL.md` is ~435 lines across 13 scannable sections:

1. **Mindset** — "Sign on the wall vs. locked door": encode invariants in C types, compiler
   flags, and build checks rather than prose comments.
2. **Before you hand back code** — formatting, `clang-tidy`, `check_arch.py`, target build,
   and host `gcc` unit test verification gates.
3. **Architecture across all C files (`app`, `bsp`, `config`, `drv`, `libs`)** — what lives in
   each layer, strict `#include` isolation, and how `libs/` and `config/` stay 100%
   hardware-independent.
4. **Configuration tables and `.rodata` Flash discipline** — Beningo `const` configuration
   tables in Flash paired with `_Static_assert` length proofs.
5. **Opaque handles and module state** — static instance pools and channel-indexed state with
   zero heap allocation.
6. **Types, physical units, and naming** — `module_ActionNoun()` public APIs, `static` private
   helpers, `ModuleConfig_t` types, `_mv`/`_ma`/`_hz`/`_ms` suffixes, and zero-cost single-field
   struct wrappers (`FreqHz_t`, `DutyPermille_t`, `Millivolts_t`).
7. **Errors, assertions, and contracts** — `__attribute__((warn_unused_result))` status enums,
   entry parameter checks, and permanent precondition assertions.
8. **Control flow, bounded loops, and watchdog liveness** — NASA JPL Power of 10: no `goto`,
   `setjmp`, `alloca`, recursion, or VLAs; mandatory timeout counters on all hardware register
   polling loops; bounded RTOS waits (`[RTOS-WDT-01]`) with rendezvous watchdog supervision;
   functions <= 60 lines.
9. **Interrupts, `volatile`, atomic safety, and RTOS concurrency** — minimal ISRs that use only
   `FromISR` OS primitives, critical sections around shared multi-byte or read-modify-write
   state, priority-inheriting mutexes for shared buses, no bit-fields to map registers, and no
   RTOS headers in `src/app/*.h`.
10. **Dual-target seams and host unit testing** — Grenning link-time substitution swapping
    hardware layers for fakes/spies without `#ifdef TEST` clutter, plus Humble Object split.
11. **Standardized file layout and Doxygen hygiene** — `@file`/`@brief` headers and fixed
    section divider banners across every `.h` and `.c` file.
12. **Compiler flags and static analysis** — the locked-door C11 pedantic flag set.
13. **Final checklist** — 10 binary checks before returning code.

## Layout

```text
.
├── .claude-plugin/
│   ├── plugin.json                                    plugin manifest
│   └── marketplace.json                               self-hosted marketplace manifest
├── .github/
│   └── workflows/check.yml                            CI: skills, lints, and examples gates
├── AGENTS.md                                          contributor and repository guidelines
├── CLAUDE.md                                          Claude Code instructions
├── CONTRIBUTING.md                                    contributor setup and verification gates
├── examples/
│   └── review-motor-ctrl.md                           unedited review report on the eval fixture
├── lints/
│   ├── .clang-format                                  mandatory braces, 100-col, deterministic layout
│   ├── .clang-tidy                                    bugprone, cert, readability, <=60-line functions
│   ├── .clangd                                        cross-compiler flag filter & strict includes
│   ├── CMakeLists.txt                                 dual-target CMake build + CTest host unit tests
│   ├── Makefile                                       dual-target MCU cross-build + host GCC test runner
│   ├── check_arch.py                                  C11 safety + RTOS concurrency + layer boundary gate
│   ├── check/                                         deliberate-violation fixtures, one per arch rule
│   └── scaffold.py                                    scaffolder for full project or app/bsp/config/drv/lib
├── scripts/
│   ├── check-skill.py                                 manifests, changelog, links, frontmatter, evals
│   ├── check-lints.py                                 every arch rule fires + scaffold round-trip proof
│   ├── check-examples.py                              compiles every C11 snippet in the repo
│   └── examples.json                                  snippet manifest consumed by check-examples.py
├── skills/
│   ├── embedded-c-best-practices/
│   │   ├── SKILL.md                                   the writing skill
│   │   ├── references/
│   │   │   ├── beningo-reusable-firmware.md           Beningo 4-layer architecture & const config tables
│   │   │   ├── grenning-embedded-tdd.md               Grenning dual-target seams, fakes/spies, ADTs
│   │   │   ├── nasa-jpl-power-of-10.md                Holzmann's 10 rules for safety-critical C
│   │   │   ├── barr-c-coding-standard.md              BARR-C:2018 naming, braces, const/volatile, ISRs
│   │   │   ├── misra-and-type-safety.md               MISRA Essential Type Model & 0-cost unit wrappers
│   │   │   └── rtos-and-isr-frameworks.md             RTOS tasks, FromISR rules, mutexes, watchdog
│   │   └── evals/                                     4 writing eval cases (40 graders)
│   ├── embedded-c-port/
│   │   ├── SKILL.md                                   the cross-MCU porting skill
│   │   └── evals/                                     2 cross-MCU porting eval cases (24 graders)
│   └── embedded-c-review/
│       ├── SKILL.md                                   the code review skill
│       └── evals/                                     2 review eval cases (24 graders)
└── tests/
    └── test_check_skill.py                            unit tests for scripts/check-skill.py
```

## Testing the skills

Each skill directory includes graded evaluation tasks under `evals/`. Across the three skills
there are eight suites, totaling 88 binary graders:

| Skill | Eval suite | Graders |
| --- | --- | --- |
| `embedded-c-best-practices` | `ring-buffer-lib` | 10 |
| `embedded-c-best-practices` | `app-thermal-fsm-and-bsp` | 8 |
| `embedded-c-best-practices` | `refactor-motor-ctrl` | 12 |
| `embedded-c-best-practices` | `rtos-watchdog-supervisor` | 10 |
| `embedded-c-review` | `review-motor-ctrl` | 12 |
| `embedded-c-review` | `review-rtos-comms-task` | 12 |
| `embedded-c-port` | `port-monolith-adc-temp-mcu-a-to-b` | 12 |
| `embedded-c-port` | `port-layered-pwm-spi-drv-mcu-a-to-b` | 12 |

Run them from inside a skill folder with:

```bash
claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
```

The repository also verifies itself, and CI runs the same gates on every push and pull
request:

```bash
python3 scripts/check-skill.py     # frontmatter, manifests, changelog, links, rule IDs, evals
python3 scripts/check-lints.py     # every check_arch.py rule fires; scaffold round-trip is clean
python3 scripts/check-examples.py  # every C11 snippet compiles under -Werror
python3 -m unittest discover -s tests
claude plugin validate .
```

## Sources and attribution

The six digests in `skills/embedded-c-best-practices/references/` are original, paraphrased
summaries written for this repository that restate each authority's engineering principles in
condensed form and cite the original work:

| Source | Author / Organization | Reference |
| --- | --- | --- |
| *Reusable Firmware Development* | Jacob Beningo (Apress, 2017) | ISBN 978-1-4842-3296-5 |
| *Test-Driven Development for Embedded C* | James W. Grenning (Pragmatic Bookshelf, 2011) | ISBN 978-1-934356-62-3 |
| *The Power of 10: Rules for Developing Safety-Critical Code* | Gerard J. Holzmann (NASA JPL / IEEE Computer, 2006) | DOI `10.1109/MC.2006.212` |
| *BARR-C:2018 Embedded C Coding Standard* | Michael Barr (Barr Group, 2018) | Public HTML / CC BY-ND 4.0 (original text) |
| *MISRA C:2012 / MISRA C:2023 Essential Type Model* | MISRA Consortium | https://www.misra.org.uk/ |
| *RTOS & ISR framework conventions* | Real-time kernel and RTOS framework documentation | Framework reference manuals (task entry signatures, `FromISR` primitives, static allocation, priority-inheriting mutexes, watchdog services) |

The RTOS digest ([`rtos-and-isr-frameworks.md`](skills/embedded-c-best-practices/references/rtos-and-isr-frameworks.md))
has no single book behind it: it distills conventions that hardware-vector and RTOS framework
documentation impose on application code, so it never argues with a framework's mandated
signatures or names — it only constrains what the firmware around them may do.

The skill text, paraphrased digests, lint configurations, scaffolding tools, and evaluation
suites in this repository are MIT licensed.

## License

MIT. See [LICENSE](LICENSE).
