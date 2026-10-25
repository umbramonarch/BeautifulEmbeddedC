#!/usr/bin/env python3
"""BeautifulEmbeddedC Architecture & Safety Gate (check_arch.py).

Enforces universal C11 safety invariants across ALL .c and .h files and verifies
layer dependency boundaries across `app`, `config`, `bsp`, `drvs`, and `libs`:

1. [BENINGO-ARCH-01..03] Strict downward #include boundaries across app, config, bsp, drvs, libs.
2. [BENINGO-HDR-01]      Public .h headers must be 100% free of vendor SDK headers & register types.
3. [BENINGO-CFG-CONST]   Configuration tables (*ConfigTable / *Config[]) must be `const` in .rodata
                         and paired with `_Static_assert` in .c files ([MISRA-STATIC-ASSERT]).
4. [BENINGO-LAYOUT-01]   Standardized Doxygen `@file`/`@brief` header and `//---...---//` banners.
5. [GRENNING-SEAM-01]    No `#ifdef TEST` / `#ifdef UNIT_TEST` inside production .c/.h files.
6. [JPL-1]               Ban `goto`, `setjmp`, `longjmp`.
7. [JPL-2]               Ban unbounded hardware register polling loops (`while (...);`).
8. [JPL-3]               Ban dynamic memory (`malloc`, `calloc`, `realloc`, `free`) and `<stdio.h>`
                         formatting (`printf`, `sprintf`, `snprintf`, `vsprintf`) in production.
9. [JPL-4]               Functions in production code must not exceed 60 lines (non-blank/comment).
10.[MISRA-NO-FLOAT]      Ban `float` and `double` in production firmware unless `--allow-float`.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
from typing import List, Sequence, Tuple

BANNED_HEAP_STDIO_RE = re.compile(
    r"\b(malloc|calloc|realloc|free|printf|sprintf|snprintf|vsprintf)\s*\("
)
BANNED_CONTROL_FLOW_RE = re.compile(r"\b(goto|setjmp|longjmp)\b")
FLOAT_TYPE_RE = re.compile(r"\b(float|double)\b")
IFDEF_TEST_RE = re.compile(
    r"^\s*#\s*(?:ifdef|ifndef|if)\s+.*\b(TEST|UNIT_TEST|MODUL_TESTING)\b",
    re.MULTILINE,
)
INCLUDE_RE = re.compile(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', re.MULTILINE)
VENDOR_INCLUDE_RE = re.compile(
    r"(^|/)(stm32|nrf|esp_|driverlib|cmsis|msp\.h|vendor_|hal_|sam[d|e|v]|fsl_)",
    re.IGNORECASE,
)
VENDOR_REG_TYPE_RE = re.compile(r"\b[A-Za-z0-9_]+_(Regs|TypeDef)\s*\*")
SECTION_BANNER_RE = re.compile(r"^//-{40,}//\s*$", re.MULTILINE)
DOXYGEN_FILE_RE = re.compile(r"@file\b")
DOXYGEN_BRIEF_RE = re.compile(r"@brief\b")

# Matches `while (<cond>);` or `while (<cond>) {}` without any loop counter increment/decrement
UNBOUNDED_WHILE_SEMI_RE = re.compile(
    r"\bwhile\s*\(([^;{}]+)\)\s*;",
    re.MULTILINE,
)
UNBOUNDED_WHILE_EMPTY_BLOCK_RE = re.compile(
    r"\bwhile\s*\(([^;{}]+)\)\s*\{\s*\}",
    re.MULTILINE,
)

# Matches top-level config table definitions or extern declarations
CONFIG_TABLE_DECL_RE = re.compile(
    r"^(?:extern\s+)?(?:const\s+)?[A-Za-z_][A-Za-z0-9_]*\s+"
    r"([A-Za-z_][A-Za-z0-9_]*(?:ConfigTable|motorConfig|Config)\s*\[[^\]]*\])\s*(?:=|;)",
    re.MULTILINE,
)

FUNC_START_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_\s\*]*\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{",
    re.MULTILINE,
)


def strip_comments_keep_newlines(text: str) -> str:
    """Replace comments with spaces while preserving line numbers."""

    def _repl(match: re.Match[str]) -> str:
        s = match.group(0)
        return "".join("\n" if ch == "\n" else " " for ch in s)

    pattern = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
    return pattern.sub(_repl, text)


def line_number_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def is_test_or_vendor_path(rel_parts: Tuple[str, ...]) -> Tuple[bool, bool]:
    lower_parts = [p.lower() for p in rel_parts]
    is_vendor = "vendor_sdk" in lower_parts or "third_party" in lower_parts
    is_test = (
        "test" in lower_parts
        or "tests" in lower_parts
        or "fakes" in lower_parts
        or "evals" in lower_parts
        or any(p.startswith(("test_", "fake_")) for p in lower_parts)
    )
    return is_test, is_vendor


def classify_layer(rel_parts: Tuple[str, ...]) -> str:
    """Return one of: 'app', 'config', 'bsp', 'bsp_config', 'drv', 'libs', 'other'."""
    parts = [p.lower() for p in rel_parts]
    if len(parts) >= 2 and parts[0] == "src":
        if parts[1] == "app":
            return "app"
        if parts[1] == "config":
            return "config"
        if parts[1] == "bsp":
            if len(parts) >= 3 and parts[2] == "config":
                return "bsp_config"
            return "bsp"
    if parts and parts[0] in ("drvs", "drv"):
        return "drv"
    if parts and parts[0] in ("libs", "lib"):
        return "libs"
    return "other"


def check_function_lengths(
    rel_path: str, stripped_text: str, max_lines: int = 60
) -> List[str]:
    errors: List[str] = []
    lines = stripped_text.splitlines()
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        # Detect start of a function at column 0 (not struct/enum/typedef)
        stripped = line.strip()
        if (
            not line.startswith((" ", "\t", "#", "//"))
            and "{" in line
            and "(" in line
            and not stripped.startswith(("typedef", "struct", "enum", "union"))
        ):
            start_line = i + 1
            brace_depth = line.count("{") - line.count("}")
            code_lines = 0
            j = i + 1
            while j < n and brace_depth > 0:
                cur = lines[j]
                brace_depth += cur.count("{") - cur.count("}")
                if cur.strip():
                    code_lines += 1
                j += 1
            if code_lines > max_lines:
                errors.append(
                    f"[ARCH-ERROR] {rel_path}:{start_line}: [JPL-4] Function body is "
                    f"{code_lines} non-blank lines (max {max_lines}). Extract static helpers."
                )
            i = max(j, i + 1)
        else:
            i += 1
    return errors


def check_file(
    file_path: pathlib.Path,
    root: pathlib.Path,
    require_banners: bool = True,
    allow_float: bool = False,
) -> List[str]:
    errors: List[str] = []
    rel_path = file_path.relative_to(root).as_posix()
    rel_parts = file_path.relative_to(root).parts
    is_test, is_vendor = is_test_or_vendor_path(rel_parts)
    if is_vendor:
        return errors

    raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    clean_text = strip_comments_keep_newlines(raw_text)
    suffix = file_path.suffix.lower()
    layer = classify_layer(rel_parts)

    # 1. Standardized Doxygen @file/@brief and section banners (production files)
    if require_banners and not is_test:
        if not DOXYGEN_FILE_RE.search(raw_text) or not DOXYGEN_BRIEF_RE.search(raw_text):
            errors.append(
                f"[ARCH-ERROR] {rel_path}:1: [BENINGO-LAYOUT-01] Missing Doxygen "
                f"'@file' or '@brief' header block."
            )
        if len(SECTION_BANNER_RE.findall(raw_text)) < 3:
            errors.append(
                f"[ARCH-ERROR] {rel_path}:1: [BENINGO-LAYOUT-01] Missing standardized "
                f"'//---...---//' section divider banners."
            )

    # 2. Universal safety checks on production code
    if not is_test:
        for m in BANNED_HEAP_STDIO_RE.finditer(clean_text):
            ln = line_number_for_offset(clean_text, m.start())
            fn = m.group(1)
            errors.append(
                f"[ARCH-ERROR] {rel_path}:{ln}: [JPL-3] Forbidden dynamic allocation or "
                f"stdio call '{fn}()'."
            )

        for m in BANNED_CONTROL_FLOW_RE.finditer(clean_text):
            ln = line_number_for_offset(clean_text, m.start())
            kw = m.group(1)
            errors.append(
                f"[ARCH-ERROR] {rel_path}:{ln}: [JPL-1] Forbidden control-flow construct '{kw}'."
            )

        if not allow_float:
            for m in FLOAT_TYPE_RE.finditer(clean_text):
                ln = line_number_for_offset(clean_text, m.start())
                ft = m.group(1)
                errors.append(
                    f"[ARCH-ERROR] {rel_path}:{ln}: [MISRA-NO-FLOAT] Forbidden floating-point "
                    f"type '{ft}'; use fixed-width integer physical units (_mv, _ma, _hz, _permille)."
                )

        for m in IFDEF_TEST_RE.finditer(clean_text):
            ln = line_number_for_offset(clean_text, m.start())
            errors.append(
                f"[ARCH-ERROR] {rel_path}:{ln}: [GRENNING-SEAM-01] Forbidden '#ifdef {m.group(1)}' "
                f"in production code; use link-time substitution instead."
            )

        for regex in (UNBOUNDED_WHILE_SEMI_RE, UNBOUNDED_WHILE_EMPTY_BLOCK_RE):
            for m in regex.finditer(clean_text):
                cond = m.group(1)
                if "--" not in cond and "++" not in cond:
                    ln = line_number_for_offset(clean_text, m.start())
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [JPL-2] Unbounded polling loop "
                        f"'while ({cond.strip()})' has no timeout counter."
                    )

        if suffix == ".c":
            errors.extend(check_function_lengths(rel_path, clean_text, max_lines=60))

    # 3. Public header purity ([BENINGO-HDR-01])
    includes = [
        (m.group(1), line_number_for_offset(clean_text, m.start()))
        for m in INCLUDE_RE.finditer(clean_text)
    ]
    if suffix == ".h" and not is_test:
        for inc, ln in includes:
            if VENDOR_INCLUDE_RE.search(inc):
                errors.append(
                    f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-HDR-01] Vendor/MCU header "
                    f"'{inc}' leaked into public header."
                )
        for m in VENDOR_REG_TYPE_RE.finditer(clean_text):
            ln = line_number_for_offset(clean_text, m.start())
            errors.append(
                f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-HDR-01] Hardware register pointer "
                f"'{m.group(0).strip()}' leaked into public header."
            )

    # 4. Configuration table const + _Static_assert checks ([BENINGO-CFG-CONST])
    if not is_test:
        for m in CONFIG_TABLE_DECL_RE.finditer(clean_text):
            decl_line = m.group(0)
            if "typedef" in decl_line:
                continue
            ln = line_number_for_offset(clean_text, m.start())
            if not re.search(r"\bconst\b", decl_line):
                errors.append(
                    f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-CFG-CONST] Configuration table "
                    f"'{m.group(1).strip()}' must be qualified 'const' so it stays in .rodata Flash."
                )
            if suffix == ".c" and "extern" not in decl_line:
                if "_Static_assert" not in clean_text:
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [MISRA-STATIC-ASSERT] Configuration "
                        f"table definition in '{rel_path}' must be paired with '_Static_assert'."
                    )

    # 5. Layer-specific #include boundary checks ([BENINGO-ARCH-01..03])
    if not is_test:
        for inc, ln in includes:
            inc_name = pathlib.PurePosixPath(inc).name.lower()
            if layer == "app":
                if (
                    VENDOR_INCLUDE_RE.search(inc)
                    or inc_name.startswith("drv")
                    or inc.startswith("drvs/")
                    or (inc_name.startswith("bsp") and "cfg" in inc_name)
                ):
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-ARCH-01] 'app' layer must not "
                        f"include '{inc}' (allowed: own .h, src/bsp/bsp*.h, src/config/*.h, libs/)."
                    )
            elif layer == "config":
                if (
                    VENDOR_INCLUDE_RE.search(inc)
                    or inc_name.startswith(("app", "bsp", "drv"))
                    or inc.startswith(("src/app", "src/bsp", "drvs/", "libs/"))
                ):
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-ARCH-03] 'config' layer must "
                        f"stay pure and must not include '{inc}'."
                    )
            elif layer in ("bsp", "bsp_config"):
                if VENDOR_INCLUDE_RE.search(inc) or inc_name.startswith("app"):
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-ARCH-01] 'bsp' layer must not "
                        f"include '{inc}' (vendor SDK and app headers are forbidden in BSP)."
                    )
            elif layer == "drv":
                if inc_name.startswith(("app", "bsp")) or inc.startswith(("src/app", "src/bsp")):
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-ARCH-01] 'drv' layer must not "
                        f"depend upward on '{inc}'."
                    )
            elif layer == "libs":
                if (
                    VENDOR_INCLUDE_RE.search(inc)
                    or inc_name.startswith(("app", "bsp", "drv"))
                    or inc.startswith(("src/app", "src/bsp", "drvs/"))
                ):
                    errors.append(
                        f"[ARCH-ERROR] {rel_path}:{ln}: [BENINGO-ARCH-02] Pure vertical 'libs/' "
                        f"module must not include hardware or upper-layer header '{inc}'."
                    )

    return errors


def check_elf_symbols(elf_path: pathlib.Path) -> List[str]:
    errors: List[str] = []
    if not elf_path.is_file():
        return [f"[ARCH-ERROR] ELF file not found: {elf_path}"]

    for nm_bin in ("arm-none-eabi-nm", "nm"):
        try:
            proc = subprocess.run(
                [nm_bin, "--defined-only", str(elf_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            break
        except (FileNotFoundError, subprocess.CalledProcessError):
            proc = None
    if proc is None:
        return errors

    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        sym_type, sym_name = parts[-2], parts[-1]
        if sym_name in ("malloc", "_malloc_r", "free", "_free_r", "_sbrk"):
            errors.append(
                f"[ARCH-ERROR] {elf_path.name}: [JPL-3] Linked binary contains banned heap "
                f"symbol '{sym_name}'."
            )
        if "ConfigTable" in sym_name and sym_type in ("D", "d", "B", "b"):
            errors.append(
                f"[ARCH-ERROR] {elf_path.name}: [BENINGO-CFG-CONST] '{sym_name}' is in SRAM "
                f"(section '{sym_type}'); qualify it 'const' so it stays in .rodata Flash."
            )
    return errors


def collect_c_files(target: pathlib.Path) -> List[pathlib.Path]:
    if target.is_file():
        return [target]
    files: List[pathlib.Path] = []
    for ext in ("*.h", "*.c"):
        for p in sorted(target.rglob(ext)):
            if "build" in p.parts or ".git" in p.parts:
                continue
            files.append(p)
    return files


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Embedded C architecture boundaries and safety-critical C11 rules."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Directories or .c/.h files to check (default: current directory).",
    )
    parser.add_argument(
        "--no-banner-check",
        action="store_true",
        help="Skip Doxygen @file/@brief and section banner checks on legacy files.",
    )
    parser.add_argument(
        "--allow-float",
        action="store_true",
        help="Permit float/double types on targets with a hardware FPU.",
    )
    parser.add_argument(
        "--elf",
        type=pathlib.Path,
        default=None,
        help="Optional linked .elf binary to inspect for heap and .rodata placement.",
    )
    args = parser.parse_args(argv)

    all_errors: List[str] = []
    checked_count = 0

    for raw_target in args.paths:
        target = pathlib.Path(raw_target).resolve()
        root = target if target.is_dir() else target.parent
        for c_file in collect_c_files(target):
            is_test, is_vendor = is_test_or_vendor_path(c_file.relative_to(root).parts)
            if is_vendor:
                continue
            checked_count += 1
            all_errors.extend(
                check_file(
                    c_file,
                    root=root,
                    require_banners=not args.no_banner_check,
                    allow_float=args.allow_float,
                )
            )

    if args.elf is not None:
        all_errors.extend(check_elf_symbols(args.elf))

    if all_errors:
        for err in all_errors:
            print(err, file=sys.stderr)
        print(
            f"[ARCH-FAIL] {len(all_errors)} violation(s) across {checked_count} file(s).",
            file=sys.stderr,
        )
        return 1

    print(f"[ARCH-OK] {checked_count} file(s) passed all architecture and safety checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
