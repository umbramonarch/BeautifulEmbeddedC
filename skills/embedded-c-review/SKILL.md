---
name: embedded-c-review
description: >-
  Review existing Embedded C code (.c and .h files across app, bsp, config, drv, libs, ISRs,
  and unit tests) for safety, bounded execution, concurrency, layer architecture, type safety,
  and maintainability, and produce a prioritized report where every finding cites the rule it
  breaks and gives a concrete fix. Use this whenever the user asks to review, audit, critique,
  grade, or "check" Embedded C or firmware code, a module, a driver, a state machine, a diff,
  or a pull request, or asks what is wrong with their C code or how to make it safer or more
  testable, even if they don't say "review". Pairs with the embedded-c-best-practices skill,
  which covers writing and refactoring code.
---

# Embedded C review

Review Embedded C code against the same five authorities the `embedded-c-best-practices` skill
uses for writing it (Jacob Beningo, James Grenning, NASA JPL Power of 10, BARR-C:2018, and the
MISRA C Essential Type Model). The output is a **review, not a rewrite**: the reader decides
what to fix. Only modify or rewrite source files when the user explicitly asks for that.

## 1. Decide the scope

- **Identify what to read.** Read the `.h` and `.c` files, modules, or `git diff` the user
  named. If they said "review this repo" or "review this module" without naming files, inspect
  the directory layout (`src/app/`, `src/bsp/`, `src/config/`, `drvs/`, `libs/`, `tests/`) and
  read the relevant headers and implementation files.
- **Classify the firmware layer(s).** Determine whether each reviewed file is an application
  state machine (`app`), board support wrapper (`bsp`), configuration header/table (`config`),
  hardware peripheral driver (`drv`), pure algorithmic library (`libs`), or a mixed/standalone
  module. **State which layer(s) you identified at the top of the report**, because layer rules
  determine which `#include`s and hardware accesses are legal.
- **Check toolchain and target constraints.** Inspect the `Makefile`, `CMakeLists.txt`, or
  compiler flags if present to see the C standard (`-std=c11`), target architecture
  (Cortex-M, RISC-V, AVR, etc.), and whether a hardware FPU is present.

## 2. Run the tools first, if you can

If you have shell access and the project has a build or lint setup, run the static checks
before reading line by line:

```bash
clang-format --dry-run -Werror <files>
python3 lints/check_arch.py .
clang-tidy <files>
make test
```

- **Fold tool findings into the report, not as a raw log dump.** Group repeated warnings (such
  as ten unbraced `if` statements or six implicit sign conversions) into a single finding that
  lists the affected line numbers.
- **Degrade gracefully.** If `clang-tidy`, `check_arch.py`, or a compiler is not installed in
  the environment, perform the checks by inspection and note in the opening paragraph which
  automated tools were or were not run.

## 3. What to look for, in priority order

Work through these five categories in order. The first two categories are where field lockups,
memory corruption, and race conditions live.

**1. Safety, memory, and bounded execution (NASA JPL Power of 10 & RTOS safety)**
- Unbounded hardware polling loops (`while (!(REG & FLAG));` or `while (HAL_Busy()) {}`) with
  no timeout counter and no `STATUS_ERR_TIMEOUT` recovery path (`[JPL-2]`).
- Infinite RTOS blocking waits (`portMAX_DELAY` / `K_FOREVER`) in watchdog-monitored tasks, or
  individual tasks kicking the hardware watchdog directly instead of reporting heartbeats to a
  supervisor task (`[RTOS-WDT-01]`).
- Dynamic memory allocation (`malloc`, `calloc`, `realloc`, `free`), dynamic RTOS object
  creation (`xTaskCreate`, `xQueueCreate`, `xSemaphoreCreateMutex`, `xSemaphoreCreateBinary`
  instead of `*Static` variants), or `<stdio.h>` formatting (`printf`, `sprintf`) that pulls in
  heap allocation (`[JPL-3]`, `[MISRA-21.3]`, `[RTOS-STATIC-01]`).
- Recursion (direct or indirect), `goto`, `setjmp`/`longjmp`, or variable-length arrays (VLAs)
  that make worst-case stack usage unprovable (`[JPL-1]`).
- Missing `NULL` pointer checks, unvalidated channel indices (`channel >= s_numChannels`), or
  buffer accesses without bounds checks at function entry (`[JPL-5]`, `[JPL-7]`).
- Side effects inside `ASSERT()` macros (`[JPL-5]`).

**2. Concurrency, ISR, RTOS synchronization, and `volatile` correctness (BARR-C:2018 & RTOS)**
- Variables or buffers shared between an ISR and main-loop/task code that lack `volatile`
  (`[BARR-1.8.c]`), lack a save/restore critical section around multi-byte reads or
  read-modify-write updates like `counter++`, or re-enable interrupts unconditionally with
  `__enable_irq()` instead of restoring the saved interrupt mask (`[BARR-ISR-ATOMIC]`).
- Calling blocking or non-`FromISR` RTOS primitives (`xQueueSend`, `xQueueReceive`,
  `xSemaphoreTake`, `vTaskDelay`) inside an `*_IRQHandler` instead of `xQueueSendFromISR` /
  `vTaskNotifyGiveFromISR` + `portYIELD_FROM_ISR()` (`[RTOS-ISR-01]`).
- Using a binary semaphore (`xSemaphoreCreateBinary`) instead of a priority-inheriting mutex
  (`xSemaphoreCreateMutexStatic`) to lock a shared hardware bus (SPI, I2C, RS-485) across tasks,
  risking unbounded priority inversion (`[RTOS-MUTEX-01]`).
- Heavy work inside an ISR: polling loops, floating-point math, or full state-machine
  execution instead of setting a flag or pushing to a lock-free ring buffer (`[BARR-6.5]`).
- Hardware MMIO pointers missing `volatile`, or C struct bit-fields overlaid onto hardware
  registers instead of explicit `_POS` and `_MASK` macros (`[BARR-NO-BITFIELDS]`).

**3. Architecture, layer isolation, and `.rodata` Flash (Beningo & Grenning)**
- Vendor SDK headers (`stm32*.h`, `driverlib.h`, `nrf*.h`, `vendor_hal.h`) or register pointers
  leaked into any `.h` file or included inside `src/app/`, `src/bsp/`, `src/config/`, or
  `libs/` (`[BENINGO-HDR-01]`, `[BENINGO-ARCH-01]`).
- RTOS kernel headers (`FreeRTOS.h`, `task.h`, `queue.h`, `semphr.h`) leaked into public
  `src/app/*.h` headers or coupled into application state-machine logic instead of using an
  OS-agnostic `app<Name>_Step()` core / Humble Task Wrapper (`[RTOS-SEAM-01]`).
- Upward or layer-skipping `#include`s (e.g., `app` including `drv*.h` directly instead of
  `bsp*.h`, or `drv` including `app*.h`) (`[BENINGO-ARCH-01]`).
- Configuration tables (`*ConfigTable`) missing `const` (wasting SRAM in `.data` instead of
  staying in `.rodata` Flash) or missing a compile-time `_Static_assert` matching the channel
  enum count (`[BENINGO-CFG-CONST]`, `[MISRA-STATIC-ASSERT]`).
- BSP function names that expose MCU pin numbers (`bspGpio_SetPA8`) instead of board-meaningful
  domain names (`bspGpio_FaultLedSet`) (`[BENINGO-BSP-01]`).
- `#ifdef TEST` or `#ifdef UNIT_TEST` conditional compilation inside production `.c`/`.h` files
  instead of link-time substitution seams (`[GRENNING-SEAM-01]`, `[JPL-8]`).

**4. Type safety, physical units, and error handling (MISRA C & BARR-C)**
- Fallible functions returning `void`, `int`, or `bool` instead of a `MUST_CHECK`
  (`__attribute__((warn_unused_result))`) status enum, or callers ignoring returned error codes
  (`[JPL-7]`, `[MISRA-17.7]`).
- Bare `int`, `short`, `long`, or `unsigned` instead of `<stdint.h>` fixed-width types
  (`uint8_t`, `uint16_t`, `uint32_t`, `int32_t`, `size_t`) (`[BARR-5.2.a]`).
- Accidental `float` or `double` arithmetic where fixed-point physical units (`_mv`, `_ma`,
  `_hz`, `_ms`, `_permille`) belong (`[MISRA-NO-FLOAT]`).
- Raw primitive parameters for physical quantities that can be swapped at call sites instead of
  unit suffixes and single-field unit wrapper structs (`Millivolts_t`, `FreqHz_t`,
  `DutyPermille_t`) (`[BARR-UNIT-SUFFIX]`, `[MISRA-UNIT-WRAP]`).
- Implicit sign conversions, mixed signed/unsigned comparisons (`[MISRA-10.4]`), bitwise shifts
  on signed integers (`[BARR-5.3.b]`), or unsigned literals missing the `U` suffix
  (`[MISRA-7.2]`).

**5. Formatting, file layout, and host unit tests**
- Missing `{}` braces on `if`, `else`, `for`, `while`, `do`, or `switch` bodies
  (`[BARR-1.3.a]`), or `switch` statements missing a `default:` branch
  (`[BARR-8.3.b]`, `[MISRA-16.4]`).
- Functions longer than 60 lines (`[JPL-4]`) or non-`static` private helpers/variables
  (`[BARR-1.8.a]`).
- Missing `@file`/`@brief` Doxygen header, missing `//---...---//` section dividers
  (`[BENINGO-LAYOUT-01]`, `[BARR-4.3.b]`), or missing link-time fake and host unit tests
  (`[GRENNING-TEST-01]`).

### Framework conventions to leave alone (do not flag as defects)

Embedded RTOS kernels and MCU startup vector tables require specific function signatures and
task structures. **Never report these framework-mandated idioms as defects:**

- **RTOS task entry signatures (`void vTask(void *pvParameters)`):** FreeRTOS, Zephyr, and
  ThreadX mandate `void *` parameters and `void` return types for task entry functions. Casting
  unused context with `(void)pvParameters;` is compliant — do not ask to change the signature
  to return `Status_e`.
- **RTOS task superloops (`for (;;)` with bounded waits):** An RTOS task loop (`for (;;)`) that
  yields the CPU on every iteration via a finite-timeout OS primitive (`pdMS_TO_TICKS(50U)`,
  `vTaskDelayUntil`) is the standard task structure, not an unbounded hardware polling loop
  (`[JPL-2]`). Only flag the loop if it spins without blocking or blocks indefinitely with
  `portMAX_DELAY` / `K_FOREVER` (`[RTOS-WDT-01]`).
- **Linker-mandated hardware vector names (`void USART2_IRQHandler(void)`):** Startup vector
  tables bind weak ISR symbols by exact name (`TIM1_UP_IRQHandler`, `USART2_IRQHandler`,
  `SysTick_Handler`). They **must have external linkage** (never advise marking an
  `*_IRQHandler` `static` or renaming it to `module_ActionNoun()`, which breaks linker vector
  binding).
- **Vendor HAL/DMA callbacks (`HAL_UART_RxCpltCallback`):** Weak vendor SDK callbacks are valid
  inside `drvs/<periph>/drv*.c` (flag them only if placed in `src/bsp/` or `src/app/`).

The `embedded-c-best-practices` skill and its `references/` folder (including
`references/rtos-and-isr-frameworks.md`) hold the full rules and code templates. If it is
installed, read the relevant reference when a finding needs a specific rule citation or pattern.

## 4. Write the report

Use this exact report structure:

~~~markdown
# Embedded C review: <what was reviewed>

<One paragraph: what the code does, which firmware layer(s) it belongs to (app, bsp, config,
drv, libs, or mixed), overall verdict, and the single most important defect to fix. State
whether clang-format, clang-tidy, check_arch.py, and host unit tests were run.>

## Must fix

### 1. <Short title> (`path/to/file.c:42`)
**Rule:** <Rule ID and source authority, e.g. "`[JPL-2]` Fixed upper bounds on all loops (NASA
JPL Power of 10)" or "`[BENINGO-HDR-01]` Vendor-free public headers (Beningo, Reusable Firmware
Development)">
**Problem:** <What is wrong and the concrete failure mode in the field or build, in 1–2
sentences.>
**Fix:**
```c
<the smallest code change that fixes the defect>
```

## Should fix

### 2. ...

## Consider

### 3. ...

## What's already good
- <2 to 4 specific things the code already does well, with file:line references where helpful>
~~~

### How to sort findings

- **Must fix:** Unbounded hardware loops, `portMAX_DELAY` / `K_FOREVER` blocking in
  watchdog-monitored tasks, `malloc`/`free` or dynamic RTOS `xTaskCreate`/`xQueueCreate`,
  blocking OS calls inside ISRs (`xQueueSend` instead of `xQueueSendFromISR`), binary semaphore
  bus locks causing priority inversion, ISR data races, unconditional `__enable_irq()`, missing
  `volatile` on MMIO/ISR state, vendor SDK or RTOS headers leaked into public `.h` files,
  missing `NULL`/bounds guards, ignored hardware error returns, `goto`/recursion/VLAs, or
  mutable configuration tables in SRAM.
- **Should fix:** Bare `int`/`float` types, missing physical unit suffixes or wrapper structs,
  missing `MUST_CHECK` annotations, non-`static` private helpers/state (except linker vector
  `*_IRQHandler` symbols), unbraced control statements, missing `default:` in `switch`, mixed
  signed/unsigned arithmetic, or functions exceeding 60 lines.
- **Consider:** Standardized section divider ordering, Doxygen `@param`/`@return` completeness,
  naming refinements, and additional host unit test cases.

### Rules for each finding

- **Cite an exact location** as `file.c:line` or `file.c:start-end` (write `whole file` only
  for file-wide issues such as missing section banners or missing unit tests).
- **Cite a named, look-up-able rule and its authority** (e.g. `[BENINGO-HDR-01]`,
  `[BENINGO-CFG-CONST]`, `[GRENNING-SEAM-01]`, `[JPL-1]`..`[JPL-10]`, `[BARR-1.3.a]`,
  `[BARR-5.2.a]`, `[BARR-ISR-ATOMIC]`, `[BARR-NO-BITFIELDS]`, `[MISRA-10.3]`, `[MISRA-16.4]`,
  `[MISRA-17.7]`, `[MISRA-21.3]`, `[MISRA-UNIT-WRAP]`, `[RTOS-STATIC-01]`, `[RTOS-ISR-01]`,
  `[RTOS-MUTEX-01]`, `[RTOS-WDT-01]`, `[RTOS-SEAM-01]`).
- **Show the fix as a minimal C code snippet**, limited to the lines that change. Never paste a
  complete rewritten file into the review report.
- **Group repeated violations.** Report one finding for "six unbraced `if` statements (`lines
  28, 41, 59, ...`)" rather than six separate findings.
- **"What's already good" is mandatory.** Call out at least two concrete strengths in the
  existing code so the author knows what to preserve.
- **Do not modify the reviewed source files** unless the user explicitly asked you to both
  review and refactor them.

## 5. Offer the lints

If the reviewed project lacks `.clang-format`, `.clang-tidy`, or `check_arch.py`, end the
report with a short section suggesting the `BeautifulEmbeddedC` `lints/` suite
(https://github.com/umbramonarch/BeautifulEmbeddedC) and name two or three specific findings
from your review that `check_arch.py`, `.clang-format`, or `.clang-tidy` would have caught
automatically in the build.
