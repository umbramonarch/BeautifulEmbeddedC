# Michael Barr — BARR-C:2018 Embedded C Coding Standard (digest)

Source: *Embedded C Coding Standard* (BARR-C:2018) by Michael Barr (Barr Group, 2018, ISBN
978-1-72112-798-6, https://barrgroup.com/embedded-systems/books/embedded-c-coding-standard).
Read this when naming modules, functions, types, and variables, enforcing brace and operator
precedence rules, qualifying data with `const` and `volatile`, writing register access macros,
or protecting data shared with Interrupt Service Routines (ISRs).

## 1. Guiding Principles

BARR-C prioritizes **defect prevention by construction** over personal aesthetics: when a syntax
choice (such as omitting braces on a one-line `if` or mixing signed and unsigned integers) makes
a known class of bugs possible, the standard bans that syntax outright and enforces the rule
automatically through `.clang-format` and `.clang-tidy`.

## 2. Naming Conventions (`[BARR-4.1]`, `[BARR-5.1]`, `[BARR-6.1]`, `[BARR-7.1]`)

*Harmonization note:* BARR-C specifies module-prefixed functions (`module_action()`) and
distinct type suffixes (`_t`). In `BeautifulEmbeddedC`, we pair BARR-C's module prefix and
physical-unit variable suffixes with Beningo's camelCase/PascalCase boundary
(`module_ActionNoun()`, `ModuleConfig_t`) so the module boundary is visually unmistakable across
`app`, `bsp`, `config`, `drv`, and `libs`:

| Construct | Rule Code | Pattern | Examples |
| --- | --- | --- | --- |
| Public functions | `[BARR-6.1.i]` | `<module>_<ActionNoun>()` | `appThermal_RunStep()`, `bspGpio_FaultLedSet()`, `drvPwm_SetDuty()`, `ringBuf_Push()` |
| Private functions | `[BARR-6.2.d]` | `static <PascalCase>()` | `static Status_e WaitReadyFlag(uint32_t maxCycles)` |
| Interrupt handlers | `[BARR-6.5.b]` | `<periph>_Isr()` / vector name | `static void tim2_Isr(void)` |
| Struct & typedef types | `[BARR-5.1.a]` | `<PascalCase>_t` | `AppThermalConfig_t`, `DrvPwmConfig_t`, `Millivolts_t` |
| Enum types | `[BARR-5.1.b]` | `<PascalCase>_e` | `Status_e`, `BspPwmChannel_e`, `AppMode_e` |
| Enum constants & macros | `[BARR-6.1.f]` | `UPPER_SNAKE_CASE` | `STATUS_OK`, `BSP_PWM_CH_COUNT`, `ADC_TIMEOUT_CYCLES` |
| File-scope `static` vars | `[BARR-7.1]` | `s_<camelCase>[_<unit>]` | `s_isInitialized`, `s_configTable`, `s_busVoltage_mv` |
| `const` tables in `.rodata` | `[BARR-1.8.b]` | `k<PascalCase>` | `kBspPwmConfigTable`, `kNtcTempLut_degC` |
| Local variables & fields | `[BARR-7.1]` | `<camelCase>_<unit>` | `targetVoltage_mv`, `loadCurrent_ma`, `period_us`, `duty_permille` |
| Boolean variables | `[BARR-7.1.n]` | `is*`, `has*`, `can*`, `should*` | `isInitialized`, `hasFaultLatched`, `isActiveLow` |

### Physical unit suffixes (`[BARR-UNIT-SUFFIX]`)

Every variable, struct field, or constant representing a physical quantity must end with its
unit suffix (or use a unit wrapper struct from `references/misra-and-type-safety.md`):

- Voltage: `_mv` (millivolts), `_uv` (microvolts)
- Current: `_ma` (milliamps), `_ua` (microamps)
- Frequency & Time: `_hz` (hertz), `_ms` (milliseconds), `_us` (microseconds), `_ns` (nanoseconds), `_cycles`, `_ticks`
- Ratio & Temperature: `_permille` (0..1000 = 0.0%..100.0%), `_degC` (degrees Celsius), `_mdegC` (millidegrees Celsius)

## 3. Braces, Formatting, and Operator Precedence

- **`[BARR-1.3.a]` (Mandatory braces on every control block):** Every `if`, `else if`, `else`,
  `for`, `while`, `do`, and `switch` statement must have `{}` braces around its body, even when
  the body is a single line or empty. This prevents "goto fail"-style bugs when a second
  statement or macro expansion is added later. Enforced by `.clang-format` (`InsertBraces:
  true`, `AllowShortIfStatementsOnASingleLine: Never`, `AllowShortLoopsOnASingleLine: false`).
- **`[BARR-1.4.a]` (Explicit parentheses over operator precedence):** Never rely on memorized C
  operator precedence between bitwise, shift, relational, and boolean operators. Parenthesize
  every sub-expression in `&&`, `||`, `&`, `|`, and `<<`/`>>` expressions:

```c
/* BAD — relies on relative precedence of & and ==; unbraced body ([BARR-1.3.a], [BARR-1.4.a]) */
if (reg & STATUS_READY_MASK == 0U)
    return STATUS_ERR_TIMEOUT;

/* GOOD — explicit parentheses and mandatory braces */
if ((reg & STATUS_READY_MASK) == 0U) {
    return STATUS_ERR_TIMEOUT;
}
```

- **`[BARR-8.2.c]` (No assignment inside conditions):** Never write `if ((err = fn()) != 0)`.
  Assign `Status_e const status = fn();` on its own line, then test `if (status != STATUS_OK)`.
- **`[BARR-8.3.b]` (Every `switch` has a `default:`):** Always include a `default:` branch in
  every `switch` statement to catch unexpected or corrupted enum values.

## 4. Fixed-Width Types and Register Bit-Fields

- **`[BARR-5.2.a]` (Fixed-width `<stdint.h>` types only):** Never use bare `int`, `short`,
  `long`, or `unsigned int`. Use `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t`, `int8_t`,
  `int16_t`, `int32_t`, `size_t`, `uintptr_t`, and `bool` (`<stdbool.h>`). Use `char` only for
  ASCII text strings.
- **`[BARR-5.3.b]` (No bitwise operations on signed integers):** Shifting or masking a signed
  integer (`int32_t`) invokes implementation-defined or undefined behavior on sign bits. Perform
  all bitwise manipulations (`&`, `|`, `^`, `~`, `<<`, `>>`) on unsigned types (`uint32_t`) with
  `U`-suffixed constants (`1U`, `UINT32_C(1) << 4U`).
- **`[BARR-NO-BITFIELDS]` (Never map hardware registers with C struct bit-fields):** Although
  BARR-C 5.5 discusses bit-field precautions, C leaves bit-field bit ordering (endianness),
  padding, and read/write access width implementation-defined. Never overlay a C bit-field
  struct onto a memory-mapped hardware register; use explicit `_POS` and `_MASK` macros:

```c
/* BAD — implementation-defined bit order and access width on MMIO ([BARR-NO-BITFIELDS]) */
typedef struct {
    uint32_t enable : 1;
    uint32_t mode   : 3;
} CtrlReg_t;

/* GOOD — portable, deterministic shift and mask constants */
#define CTRL_REG_ENABLE_POS  (0U)
#define CTRL_REG_ENABLE_MASK (UINT32_C(0x1) << CTRL_REG_ENABLE_POS)
#define CTRL_REG_MODE_POS    (1U)
#define CTRL_REG_MODE_MASK   (UINT32_C(0x7) << CTRL_REG_MODE_POS)
```

## 5. `static`, `const`, `volatile`, and ISR Shared-Data Safety

- **`[BARR-1.8.a]` (`static` on all module-private functions and variables):** Any function or
  file-scope variable not declared in the module's public `.h` file must be marked `static` so
  it has internal linkage.
- **`[BARR-1.8.b]` (`const` everywhere possible):** Mark every read-only pointer parameter,
  lookup table, configuration table, and non-mutated local variable `const`.
- **`[BARR-1.8.c]` (`volatile` on all MMIO and ISR-shared variables):** Qualify every hardware
  register pointer and every variable written by an ISR `volatile`.
- **`[BARR-6.5]` & `[BARR-ISR-ATOMIC]` (Minimal ISRs and atomic critical sections):**
  1. Keep ISRs short and non-blocking: acknowledge the interrupt flag, write a `volatile` flag
     or push to a lock-free ring buffer, and return.
  2. `volatile` only prevents compiler caching — it does **not** guarantee atomicity. Any
     read-modify-write (`s_counter++`) or multi-word access shared between main code and an ISR
     must be wrapped in a save/restore critical section:

```c
/* BAD — race condition: read-modify-write on s_pendingEvents is non-atomic ([BARR-ISR-ATOMIC]) */
static volatile uint32_t s_pendingEvents = 0U;

void appEvents_ConsumeOne(void) {
    if (s_pendingEvents > 0U) {
        s_pendingEvents--; /* Can be preempted by ISR between load and store! */
    }
}

/* GOOD — save and restore interrupt state around the shared update */
bool appEvents_TryConsumeOne(void) {
    uint32_t const irqMask = bspIrq_SaveAndDisable();
    bool consumed = false;
    if (s_pendingEvents > 0U) {
        s_pendingEvents--;
        consumed = true;
    }
    bspIrq_Restore(irqMask);
    return consumed;
}
```

## 6. Checklist

- [ ] Do all public functions use `<module>_<ActionNoun>()` and all private helpers use `static`?
- [ ] Do all physical variables and struct fields end with a unit suffix (`_mv`, `_ma`, `_hz`,
      `_ms`, `_permille`) or use a unit wrapper struct?
- [ ] Does every `if`, `else`, `for`, `while`, `do`, and `switch` have `{}` braces?
- [ ] Are bare `int`, `short`, `long`, and register bit-fields completely absent?
- [ ] Are all ISR-shared variables marked `volatile` and protected by save/restore critical
      sections against tearing and read-modify-write races?
