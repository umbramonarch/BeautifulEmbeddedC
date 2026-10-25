# MISRA C Essential Type Model & Zero-Cost C11 Type Safety (digest)

Source: *MISRA C:2012 / MISRA C:2023 Guidelines for the Use of the C Language in Critical
Systems* (MISRA Consortium, https://www.misra.org.uk/), combined with zero-cost C11 type-safety
idioms (`_Static_assert`, single-field unit wrapper structs, and
`__attribute__((warn_unused_result))`).
Read this when designing type-safe C APIs, preventing implicit sign/narrowing/float conversions,
wrapping physical units in zero-cost structs, or writing compile-time `_Static_assert` proofs.

## 1. The MISRA Essential Type Model (Rules 10.1–10.8)

Standard C silently converts between `bool`, `char`, `enum`, signed integers, unsigned integers,
and floating-point numbers, producing subtle truncation, sign-extension, and wrap-around bugs.
The MISRA Essential Type Model partitions C expressions into six distinct categories that must
never be mixed implicitly:

| Essential Type Category | C11 Types Used in `BeautifulEmbeddedC` | Allowed Operations |
| --- | --- | --- |
| **Essentially Boolean** | `bool` (`true`, `false` from `<stdbool.h>`) | Logical operators (`!`, `&&`, `\|\|`), equality, condition of `if`/`for`/`while`/`?:` |
| **Essentially Character** | `char` | String literals and ASCII character comparisons only (never arithmetic or bitmasks) |
| **Essentially Enum** | Named `enum` (`Status_e`, `BspPwmChannel_e`) | Equality/inequality, `switch`, or explicit array indexing after bounds check |
| **Essentially Signed** | `int8_t`, `int16_t`, `int32_t`, `int64_t` | Signed arithmetic (`+`, `-`, `*`, `/`) and relational comparisons with same-sign operands |
| **Essentially Unsigned** | `uint8_t`, `uint16_t`, `uint32_t`, `uint64_t`, `size_t` | Unsigned arithmetic, array indexing, and **all bitwise/shift operations** (`&`, `\|`, `^`, `~`, `<<`, `>>`) |
| **Essentially Floating** | Avoided in integer/fixed-point firmware | Banned unless hardware FPU usage is explicitly specified (`[MISRA-NO-FLOAT]`) |

### Core Essential Type Rules

- **`[MISRA-7.2]` (Unsigned literal `U` suffix):** Append `U` to every hexadecimal, octal, or
  unsigned decimal constant (`0U`, `1000U`, `0xFFU`, `UINT32_C(1)`). Without `U`, a literal like
  `1 << 31` has signed `int` type and shifting into the sign bit is undefined behavior.
- **`[MISRA-10.1]` (No inappropriate essential types on operators):**
  - Never use a non-boolean expression as an `if`/`while` condition (`if (ptr != NULL)` and
    `if ((reg & MASK) != 0U)`, never `if (ptr)` or `if (reg & MASK)`).
  - Never apply bitwise operators (`&`, `|`, `^`, `~`, `<<`, `>>`) to signed integers or enums.
- **`[MISRA-10.3]` (No implicit narrowing or cross-category assignment):** Never assign a
  32-bit expression to a `uint16_t` or `uint8_t`, or a signed value to an unsigned variable,
  without an explicit bounds check and documented cast.
- **`[MISRA-10.4]` (No mixed signed/unsigned arithmetic or comparison):** If `int32_t error_mv
  = -50` is compared against `uint32_t limit_mv = 100U` (`if (error_mv > limit_mv)`), C promotes
  `error_mv` to `uint32_t` (`4294967246U`), evaluating `true` and triggering a false fault! Keep
  both operands in the same signedness category.
- **`[MISRA-10.6]` & `[MISRA-10.8]` (Widen before arithmetic, not after):** Cast narrow
  operands to the target width *before* multiplying or shifting so intermediate results do not
  overflow a narrow type:

```c
/* BAD — uint16_t * uint16_t promotes to signed int on 32-bit targets or overflows 16-bit */
uint16_t rawAdc = 4000U;
uint32_t scaled_uv = (uint32_t)(rawAdc * 825U);

/* GOOD — widen operands to uint32_t before multiplication ([MISRA-10.6]) */
uint16_t rawAdc = 4000U;
uint32_t scaled_uv = (uint32_t)rawAdc * 825U;
```

## 2. Zero-Cost Physical Unit Wrapper Structs (`[MISRA-UNIT-WRAP]`)

`typedef uint32_t FreqHz_t;` and `typedef uint32_t DutyPermille_t;` are weak aliases in C: the
compiler happily allows `drvPwm_Configure(duty, freq)` when the signature expects `(freq,
duty)`.

Wrapping a primitive integer inside a **single-field `struct`** creates a distinct nominal type
in C11:

```c
/* src/config/project_types.h */
typedef struct { uint32_t hz; }       FreqHz_t;
typedef struct { uint16_t permille; } DutyPermille_t; /* 0..1000 = 0.0%..100.0% */
typedef struct { int32_t  mv; }       Millivolts_t;
typedef struct { int32_t  ma; }       Milliamps_t;
typedef struct { uint32_t ms; }       Milliseconds_t;
typedef struct { uint32_t us; }       Microseconds_t;

static inline FreqHz_t freqHz_FromU32(uint32_t hz) {
    FreqHz_t const val = { .hz = hz };
    return val;
}

static inline DutyPermille_t dutyPermille_FromU16(uint16_t permille) {
    DutyPermille_t const val = { .permille = permille };
    return val;
}

static inline Millivolts_t millivolts_FromI32(int32_t mv) {
    Millivolts_t const val = { .mv = mv };
    return val;
}
```

### Why this is 100% zero-cost at runtime

| Target ABI | Single-Field Struct <= 4 Bytes (`FreqHz_t`, `DutyPermille_t`, `Millivolts_t`) | Overhead vs. Raw `uint32_t` |
| --- | --- | --- |
| **ARM AAPCS32** (`arm-none-eabi-gcc`, Cortex-M) | Passed and returned directly in `r0`–`r3` registers | **0 bytes RAM, 0 bytes Flash, 0 extra cycles** |
| **RISC-V ILP32 / LP64** | Passed and returned directly in `a0`–`a7` registers | **0 bytes RAM, 0 bytes Flash, 0 extra cycles** |
| **System V / Win64 x86-64** (Host tests) | Passed and returned directly in `rdi`/`rcx`/`rax` registers | **0 bytes RAM, 0 bytes Flash, 0 extra cycles** |

```c
/* Compile-time rejection of swapped unit arguments ([MISRA-UNIT-WRAP]) */
MUST_CHECK Status_e bspPwm_Configure(FreqHz_t freq_hz, DutyPermille_t duty_permille);

/* Calling bspPwm_Configure(duty, freq) fails to compile with:
 * error: incompatible type for argument 1 of 'bspPwm_Configure' */
```

## 3. Compile-Time Invariants with `_Static_assert` (`[MISRA-STATIC-ASSERT]`)

Use C11 `_Static_assert` to prove layout, table completeness, and range invariants at compile
time:

1. **Configuration table completeness:** Every `const` table indexed by a channel or state enum
   must assert `ARRAY_LEN(table) == (size_t)ENUM_COUNT`.
2. **Unit wrapper size:** Assert `sizeof(FreqHz_t) == sizeof(uint32_t)` so no unexpected padding
   is ever introduced.
3. **Fixed-point and timeout bounds:** Assert that compile-time scaling multipliers cannot
   overflow `uint32_t` (`_Static_assert(MAX_ADC_COUNTS <= (UINT32_MAX /MV_PER_LSB), "...");`).

```c
#define ARRAY_LEN(arr) (sizeof(arr) / sizeof((arr)[0]))

_Static_assert(ARRAY_LEN(kBspPwmConfigTable) == (size_t)BSP_PWM_CH_COUNT,
               "kBspPwmConfigTable length must match BspPwmChannel_e count");
```

## 4. Mandatory Status Checking with `MUST_CHECK` (`[MISRA-17.7]`)

MISRA Rule 17.7 and NASA JPL Rule 7 require that the value returned by a non-void function
shall always be used. Annotate every fallible prototype with `MUST_CHECK`
(`__attribute__((warn_unused_result))`) so `-Wall -Werror` turns any ignored status return into
a hard build failure:

```c
#if defined(__STDC_VERSION__) && (__STDC_VERSION__ >= 202311L)
#define MUST_CHECK [[nodiscard]]
#elif defined(__GNUC__) || defined(__clang__)
#define MUST_CHECK __attribute__((warn_unused_result))
#else
#define MUST_CHECK
#endif

MUST_CHECK Status_e appThermal_Step(Millivolts_t temp_mv,
                                    DutyPermille_t * const outFanDuty_permille);
```

## 5. Checklist

- [ ] Are `-Wconversion -Wsign-conversion -Wdouble-promotion -Werror` enabled in the build?
- [ ] Do all unsigned literals end with `U` (`0U`, `1000U`, `0xFFU`)?
- [ ] Are distinct physical quantities passed across API boundaries wrapped in single-field
      unit structs (`FreqHz_t`, `DutyPermille_t`, `Millivolts_t`, `Milliamps_t`,
      `Milliseconds_t`)?
- [ ] Is every `const` configuration or lookup table paired with a `_Static_assert` on
      `ARRAY_LEN(table) == (size_t)ENUM_COUNT`?
- [ ] Is every fallible function annotated with `MUST_CHECK` and returning a typed `Status_e`?
