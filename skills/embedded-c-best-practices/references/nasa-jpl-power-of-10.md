# Gerard Holzmann — NASA JPL Power of 10 (digest)

Source: "The Power of 10: Rules for Developing Safety-Critical Code" by Gerard J. Holzmann,
NASA JPL Laboratory for Reliable Software (*IEEE Computer*, Vol. 39, No. 6, pp. 95–99, June
2006, DOI `10.1109/MC.2006.212`).
Read this when writing or auditing control flow, hardware register polling loops, memory
allocation, function sizing, precondition assertions, pointer usage, or compiler warning gates.

## 1. The 10 Rules at a Glance

| Code | Rule Summary | Enforcement Mechanism |
| --- | --- | --- |
| **`[JPL-1]`** | Simple control flow only: no `goto`, `setjmp`/`longjmp`, VLAs, or direct/indirect recursion. | `check_arch.py`, `-Wvla`, `-Wstack-usage=128` |
| **`[JPL-2]`** | Every loop must have a statically provable fixed upper bound. | Explicit timeout counter on all hardware register polling loops |
| **`[JPL-3]`** | No dynamic memory allocation (`malloc`, `calloc`, `realloc`, `free`) after initialization. | `check_arch.py` + ELF `nm` symbol check |
| **`[JPL-4]`** | No function longer than 60 lines of code. | `.clang-tidy` (`readability-function-size`), `check_arch.py` |
| **`[JPL-5]`** | Assert preconditions and invariants (at least 2 checks per function) with explicit recovery paths. | Entry guard clauses returning `Status_e` + `_Static_assert` |
| **`[JPL-6]`** | Declare all data objects at the smallest possible scope. | `static` file scope for module state; local variables declared at first use |
| **`[JPL-7]`** | Callers must check every non-void return value; callees must validate all parameters. | `MUST_CHECK` (`warn_unused_result`) + entry parameter guards |
| **`[JPL-8]`** | Restrict preprocessor usage to `#include` and simple constant/complete-unit macros. | Ban token pasting (`##`), variadic macros, and `#ifdef TEST` clutter |
| **`[JPL-9]`** | Restrict pointer use: at most 1 level of dereferencing in expressions; avoid function pointers. | Link-time substitution instead of vtables |
| **`[JPL-10]`** | Compile from day one with all pedantic warnings enabled and `-Werror`; pass static analysis with zero warnings. | `Makefile` CFLAGS + `.clang-tidy` + `check_arch.py` |

## 2. Rule-by-Rule Guidance and Code Patterns

### `[JPL-1]` Simple, acyclic control flow

Recursion, `goto`, `setjmp`/`longjmp`, and C99 variable-length arrays (VLAs) make worst-case
stack usage and execution time impossible to bound statically.

```c
/* BAD — VLA allocates dynamic stack memory; recursion can overflow MCU RAM ([JPL-1]) */
uint16_t ComputeChecksumRecursive(const uint8_t *data, size_t len) {
    uint8_t scratch[len]; /* FORBIDDEN: VLA */
    if (len == 0U) {
        return 0U;
    }
    return (uint16_t)data[0] + ComputeChecksumRecursive(data + 1, len - 1U);
}

/* GOOD — fixed static bound and flat iterative loop ([JPL-1], [JPL-2]) */
#define CHECKSUM_MAX_BYTES (256U)

MUST_CHECK Status_e crc_ComputeSum(const uint8_t * const data,
                                   size_t len,
                                   uint16_t * const outSum) {
    if ((data == NULL) || (outSum == NULL)) {
        return STATUS_ERR_NULL_PTR;
    }
    if (len > CHECKSUM_MAX_BYTES) {
        return STATUS_ERR_INVALID_PARAM;
    }
    uint16_t acc = 0U;
    for (size_t i = 0U; i < len; ++i) {
        acc = (uint16_t)(acc + data[i]);
    }
    *outSum = acc;
    return STATUS_OK;
}
```

### `[JPL-2]` Fixed upper bounds on all loops (especially hardware polling)

The single most common cause of hard firmware lockups in the field is an unbounded hardware
register polling loop (`while (!(SPI_SR & TXE));`). If a peripheral clock is not enabled, a bus
line is shorted to ground, or an external sensor brown-outs, an unbounded loop hangs the CPU
forever (or triggers an unrecoverable watchdog reset with zero diagnostic state).

```c
/* BAD — unbounded hardware register polling loop ([JPL-2]) */
void spi_WriteByteBlocking(uint8_t byte) {
    while ((SPI1_SR & SPI_SR_TXE_MASK) == 0U) {
        /* Hangs forever if SPI1 clock is gated or peripheral faults */
    }
    SPI1_DR = byte;
}

/* GOOD — bounded loop with explicit timeout counter and Status_e return ([JPL-2]) */
#define SPI_TX_TIMEOUT_CYCLES (10000U)
_Static_assert(SPI_TX_TIMEOUT_CYCLES > 0U, "Timeout must be positive");

MUST_CHECK Status_e drvSpi_WriteByte(uint8_t byte, uint32_t maxPollCycles) {
    if (( maxPollCycles == 0U ) || ( maxPollCycles > SPI_TX_TIMEOUT_CYCLES )) {
        return STATUS_ERR_INVALID_PARAM;
    }
    for (uint32_t cycle = 0U; cycle < maxPollCycles; ++cycle) {
        if ((SPI1_SR & SPI_SR_TXE_MASK) != 0U) {
            SPI1_DR = byte;
            return STATUS_OK;
        }
    }
    return STATUS_ERR_TIMEOUT;
}
```

*Exception:* The single top-level super-loop in `main()` (`for (;;)`) is the only intentional
non-terminating loop in bare-metal firmware, and each iteration of that loop must execute in
bounded time.

### `[JPL-3]` Zero dynamic memory allocation

Never call `malloc`, `calloc`, `realloc`, or `free`, and never call `<stdio.h>` formatting
functions (`printf`, `sprintf`, `snprintf`) that internally invoke `_malloc_r` / `_sbrk` in
newlib. Use fixed-size `static` arrays, caller-provided buffers, or static object pools.

### `[JPL-4]` Short functions (<= 60 lines)

A function must fit on a single screen (<= 60 lines). When a state machine or initialization
sequence grows past 60 lines, decompose each state handler or hardware step into a named
`static` helper function.

### `[JPL-5]` & `[JPL-7]` Defensive contracts, assertions, and checked returns

1. **Every fallible function is annotated `MUST_CHECK`** (`__attribute__((warn_unused_result))`)
   and returns a typed status enum (`Status_e`).
2. **Every function checks its preconditions at entry** (`NULL` pointers, initialization state,
   channel index bounds, physical unit bounds) and returns an explicit error status instead of
   crashing or corrupting memory.
3. **Compile-time invariants use `_Static_assert`** so invalid buffer sizes or mismatched
   tables fail before the binary is even linked.
4. **Never put side effects inside an `ASSERT(expr)` macro.** If `expr` mutates state (`i++` or
   a function call), disabling or changing the assertion macro alters program behavior.

### `[JPL-8]` & `[JPL-9]` Preprocessor and pointer discipline

- Prefer `static inline` functions with typed parameters over function-like macros whenever
  possible.
- Never use `#ifdef TEST` inside production `.c` or `.h` files; use link-time substitution
  (`references/grenning-embedded-tdd.md`).
- Avoid function pointers in safety-critical paths unless strictly confined to a `const`
  dispatch table in `.rodata` with a compile-time bounded index.
- Limit pointer indirection to a single dereference (`*ptr` or `ptr->field`). The only
  permitted two-level pointer pattern is an explicit out-parameter (`DrvHandle_t * const
  outHandle`) in an initialization/open function, validated against `NULL` at entry.

## 3. Checklist

- [ ] Are there zero occurrences of `goto`, `setjmp`, `longjmp`, VLAs, or recursion?
- [ ] Does every `while` or `for` loop waiting on a hardware flag have a finite timeout counter?
- [ ] Are `malloc`, `calloc`, `realloc`, and `free` completely absent?
- [ ] Is every function body <= 60 lines?
- [ ] Does every public function validate `NULL` pointers and bounds before dereferencing?
- [ ] Does every caller check the `Status_e` returned by fallible functions?
