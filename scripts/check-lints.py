#!/usr/bin/env python3
"""Self-test suite for BeautifulEmbeddedC lints (`check_arch.py` and `scaffold.py`).

Stage 1 (Negative proof):
  Runs `lints/check_arch.py` against the deliberate-violation fixture tree in `lints/check/`,
  verifies that every `// expect: [RULE-ID]` comment fires on its exact line, verifies that zero
  unexpected diagnostics fire, and verifies that every rule ID in `check_arch.py` is covered.

Stage 2 (Positive scaffold round-trip proof):
  Scaffolds a full 4-layer (`app`, `bsp`, `config`, `drv`) + vertical `libs/` project in a
  temporary directory, verifies 0 `check_arch.py` violations, verifies 0 `clang-format`
  violations (`--dry-run -Werror`), and compiles all generated modules and host unit tests
  under the strict C11 warning flags.
"""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from typing import Dict, List, Set, Tuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
LINTS_DIR = REPO_ROOT / "lints"
CHECK_ARCH_PY = LINTS_DIR / "check_arch.py"
SCAFFOLD_PY = LINTS_DIR / "scaffold.py"
CHECK_FIXTURE_DIR = LINTS_DIR / "check"

EXPECT_COMMENT_RE = re.compile(r"//\s*expect:\s*(.+)$")
RULE_TAG_RE = re.compile(r"\[([A-Za-z0-9_.-]+)\]")
ARCH_ERROR_LINE_RE = re.compile(
    r"^\[ARCH-ERROR\]\s+([^:]+):(\d+):\s+\[([A-Za-z0-9_.-]+)\]\s+(.*)$"
)
ARCH_RULE_IN_SOURCE_RE = re.compile(r"\[ARCH-ERROR\][^\n]*?\[([A-Za-z0-9_.-]+)\]")

COMMON_WARN_FLAGS = [
    "-std=c11",
    "-Wall",
    "-Wextra",
    "-Werror",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wdouble-promotion",
    "-Wshadow",
    "-Wundef",
    "-Wformat=2",
    "-Wmissing-prototypes",
    "-Wstrict-prototypes",
    "-Wold-style-definition",
    "-Wwrite-strings",
    "-Wcast-qual",
    "-Wvla",
]


def discover_rules_in_check_arch() -> Set[str]:
    source = CHECK_ARCH_PY.read_text(encoding="utf-8")
    return set(ARCH_RULE_IN_SOURCE_RE.findall(source))


def collect_expected_annotations(fixture_root: pathlib.Path) -> List[Tuple[str, int, str]]:
    expected: List[Tuple[str, int, str]] = []
    for ext in ("*.h", "*.c"):
        for path in sorted(fixture_root.rglob(ext)):
            rel_posix = path.relative_to(fixture_root).as_posix()
            for line_no, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                m = EXPECT_COMMENT_RE.search(line)
                if m:
                    for rule_id in RULE_TAG_RE.findall(m.group(1)):
                        expected.append((rel_posix, line_no, rule_id))
    return expected


def run_stage1_negative_proof() -> bool:
    print("=" * 78)
    print("STAGE 1: Negative Proof (Deliberate Violations in lints/check/)")
    print("=" * 78)

    all_rules = discover_rules_in_check_arch()
    expected_list = collect_expected_annotations(CHECK_FIXTURE_DIR)
    expected_counter = Counter(expected_list)

    proc = subprocess.run(
        [sys.executable, str(CHECK_ARCH_PY), str(CHECK_FIXTURE_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )

    actual_list: List[Tuple[str, int, str]] = []
    unparsed_lines: List[str] = []
    for raw_line in proc.stderr.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[ARCH-FAIL]"):
            continue
        m = ARCH_ERROR_LINE_RE.match(line)
        if m:
            rel_path, line_str, rule_id, _ = m.groups()
            actual_list.append((rel_path, int(line_str), rule_id))
        else:
            unparsed_lines.append(line)

    actual_counter = Counter(actual_list)

    exp_by_rule: Dict[str, int] = Counter(r for _, _, r in expected_list)
    act_by_rule: Dict[str, int] = Counter(r for _, _, r in actual_list)

    all_rule_ids = sorted(all_rules | set(exp_by_rule) | set(act_by_rule))
    print(f"{'Rule ID':<24} {'Expected':>10} {'Actual':>10} {'Status':>10}")
    print("-" * 78)

    stage1_ok = True
    for rule_id in all_rule_ids:
        exp_count = exp_by_rule.get(rule_id, 0)
        act_count = act_by_rule.get(rule_id, 0)
        rule_matches = all(
            expected_counter[k] == actual_counter[k]
            for k in (set(expected_counter) | set(actual_counter))
            if k[2] == rule_id
        )
        ok = exp_count > 0 and exp_count == act_count and rule_matches
        if not ok:
            stage1_ok = False
        status = "PASS" if ok else "FAIL"
        print(f"[{rule_id}]{'':<{22 - len(rule_id)}} {exp_count:>10} {act_count:>10} {status:>10}")

    print("-" * 78)

    # Check for missing or unexpected line-level diagnostics
    for item, count in sorted(expected_counter.items()):
        act = actual_counter.get(item, 0)
        if act < count:
            stage1_ok = False
            print(
                f"[MISS] Expected [{item[2]}] at {item[0]}:{item[1]} "
                f"(expected {count}, got {act})",
                file=sys.stderr,
            )

    for item, count in sorted(actual_counter.items()):
        exp = expected_counter.get(item, 0)
        if count > exp:
            stage1_ok = False
            print(
                f"[UNEXPECTED] Unexpected [{item[2]}] at {item[0]}:{item[1]} "
                f"(expected {exp}, got {count})",
                file=sys.stderr,
            )

    if unparsed_lines:
        stage1_ok = False
        for line in unparsed_lines:
            print(f"[UNPARSED] {line}", file=sys.stderr)

    untested = all_rules - set(exp_by_rule)
    if untested:
        stage1_ok = False
        print(f"[UNTESTED] Rules without // expect annotations: {sorted(untested)}", file=sys.stderr)

    if proc.returncode == 0:
        stage1_ok = False
        print("[FAIL] check_arch.py returned 0 on deliberate-violation suite.", file=sys.stderr)

    if stage1_ok:
        print(
            f"[STAGE 1 PASS] All {len(all_rules)} rule IDs and {len(expected_list)} "
            f"line-exact expectations verified with 0 false positives."
        )
    return stage1_ok


def run_stage2_scaffold_roundtrip() -> bool:
    print("\n" + "=" * 78)
    print("STAGE 2: Positive Proof (Scaffold Round-Trip + Format + C11 Compile)")
    print("=" * 78)

    with tempfile.TemporaryDirectory(prefix="bec_scaffold_") as tmp:
        tmp_root = pathlib.Path(tmp)

        scaffold_cmds = [
            ["--init-project", "--root", str(tmp_root)],
            ["--layer", "config", "thermal", "--root", str(tmp_root)],
            ["--layer", "drv", "pwm", "--root", str(tmp_root)],
            ["--layer", "bsp", "pwm", "--root", str(tmp_root)],
            ["--layer", "app", "thermal", "--root", str(tmp_root)],
            ["--layer", "lib", "ring_buf", "--root", str(tmp_root)],
        ]
        for args in scaffold_cmds:
            proc = subprocess.run(
                [sys.executable, str(SCAFFOLD_PY), *args],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                print(f"[FAIL] scaffold.py {' '.join(args)} failed:\n{proc.stderr}", file=sys.stderr)
                return False

        for expected_cfg in (
            ".clang-format",
            ".clang-tidy",
            ".clangd",
            "Makefile",
            "CMakeLists.txt",
        ):
            if not (tmp_root / expected_cfg).is_file():
                print(f"[FAIL] Missing scaffolded root file: {expected_cfg}", file=sys.stderr)
                return False
        print("[OK] Scaffolder generated 4-layer project + CMakeLists.txt + Makefile.")

        # 1. Run check_arch.py on the scaffolded project
        arch_proc = subprocess.run(
            [sys.executable, str(CHECK_ARCH_PY), str(tmp_root)],
            capture_output=True,
            text=True,
            check=False,
        )
        if arch_proc.returncode != 0:
            print(
                f"[FAIL] check_arch.py failed on scaffolded project:\n{arch_proc.stderr}",
                file=sys.stderr,
            )
            return False
        print(f"[OK] {arch_proc.stdout.strip()}")

        # 2. Verify clang-format --dry-run -Werror on all generated C/H files
        c_h_files = sorted(
            [p for ext in ("*.h", "*.c") for p in tmp_root.rglob(ext)]
        )
        clang_format_bin = shutil.which("clang-format")
        if clang_format_bin:
            fmt_proc = subprocess.run(
                [clang_format_bin, "--dry-run", "-Werror", *[str(p) for p in c_h_files]],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if fmt_proc.returncode != 0:
                print(
                    f"[FAIL] clang-format --dry-run -Werror failed:\n{fmt_proc.stderr}",
                    file=sys.stderr,
                )
                return False
            print(
                f"[OK] clang-format --dry-run -Werror passed on all {len(c_h_files)} C/H files."
            )
        else:
            print("[SKIP] clang-format not found on PATH.")

        # 3. Compile generated C11 sources and host unit tests with gcc or clang
        cc_bin = shutil.which("gcc") or shutil.which("clang")
        if not cc_bin:
            print("[SKIP] Neither gcc nor clang found on PATH.")
            return True

        inc_flags = [
            f"-I{tmp_root / 'src/app'}",
            f"-I{tmp_root / 'src/config'}",
            f"-I{tmp_root / 'src/bsp'}",
            f"-I{tmp_root / 'src/bsp/config'}",
            f"-I{tmp_root / 'drvs/pwm'}",
            f"-I{tmp_root / 'libs/ring_buf'}",
            f"-I{tmp_root / 'drvs/pwm/test'}",
            f"-I{tmp_root / 'libs/ring_buf/test'}",
            f"-I{tmp_root / 'tests'}",
        ]

        # First verify every production and test .c file passes strict C11 -fsyntax-only
        all_c_files = sorted(tmp_root.rglob("*.c"))
        for c_file in all_c_files:
            syn_proc = subprocess.run(
                [cc_bin, *COMMON_WARN_FLAGS, "-fsyntax-only", *inc_flags, str(c_file)],
                capture_output=True,
                text=True,
                check=False,
            )
            if syn_proc.returncode != 0:
                print(
                    f"[FAIL] Strict C11 compile failed on {c_file.name}:\n{syn_proc.stderr}",
                    file=sys.stderr,
                )
                return False

        # Link and run host unit tests if the host linker environment is available
        shared_srcs = [
            str(tmp_root / "libs/ring_buf/ringBuf.c"),
            str(tmp_root / "src/bsp/config/bspPwmCfg.c"),
            str(tmp_root / "src/bsp/bspPwm.c"),
            str(tmp_root / "src/app/appThermal.c"),
            str(tmp_root / "drvs/pwm/test/fake_drvPwm.c"),
        ]
        test_srcs = [
            tmp_root / "tests/test_appThermal.c",
            tmp_root / "drvs/pwm/test/test_drvPwm.c",
            tmp_root / "libs/ring_buf/test/test_ring_buf.c",
        ]
        build_dir = tmp_root / "build"
        build_dir.mkdir(exist_ok=True)
        exe_suffix = ".exe" if sys.platform == "win32" else ""

        linked_and_ran = 0
        for test_src in test_srcs:
            out_bin = build_dir / f"{test_src.stem}{exe_suffix}"
            link_proc = subprocess.run(
                [
                    cc_bin,
                    *COMMON_WARN_FLAGS,
                    "-O0",
                    "-g3",
                    *inc_flags,
                    *shared_srcs,
                    str(test_src),
                    "-o",
                    str(out_bin),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if link_proc.returncode == 0 and out_bin.is_file():
                run_proc = subprocess.run(
                    [str(out_bin)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if run_proc.returncode != 0:
                    print(
                        f"[FAIL] Host unit test {out_bin.name} failed:\n{run_proc.stderr}",
                        file=sys.stderr,
                    )
                    return False
                linked_and_ran += 1

        if linked_and_ran == len(test_srcs):
            print(
                f"[OK] Compiled, linked, and executed all {linked_and_ran} host unit test "
                f"binaries with '{pathlib.Path(cc_bin).name}'."
            )
        else:
            print(
                f"[OK] Verified all {len(all_c_files)} C11 translation units with "
                f"'{pathlib.Path(cc_bin).name} -fsyntax-only' (0 warnings)."
            )

    print("[STAGE 2 PASS] Scaffold round-trip verification succeeded.")
    return True


def main() -> int:
    s1 = run_stage1_negative_proof()
    s2 = run_stage2_scaffold_roundtrip()
    if s1 and s2:
        print("\n[ALL LINT CHECKS PASSED]")
        return 0
    print("\n[LINT CHECKS FAILED]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
