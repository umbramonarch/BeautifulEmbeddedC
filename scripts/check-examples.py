#!/usr/bin/env python3
"""Compile every Embedded C code block in the documentation with the strict C11 gates.

The repository promises that every ```c block in the README, the skills, the reference
digests, and the worked examples compiles cleanly under
`-std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wsign-conversion`. This gate keeps
that promise honest:

1. **Extract.** Every top-level ```` ```c ```` / ```` ```c11 ```` fenced block in `DOC_GLOBS`
   is extracted with its exact Markdown line numbers. Fences nested inside a wider fence
   (for example the `PORTING.md` and review-report templates inside `~~~markdown`) are content,
   never blocks. `evals/` is out of scope.
2. **Synchronize.** `scripts/examples.json` must describe every extracted block: its file, its
   zero-based index, and the first non-blank line of its code. Blocks that were added, moved,
   reordered, or edited without updating the manifest are hard errors, and so are stale
   manifest entries.
3. **Compile.** `scripts/examples.json` supplies the harness: shared `headers` materialized
   into `<tmp>/include`, per-file and per-block `prelude` text, a `{code}` `template`, a
   `compile_from` marker that blanks a combined `/* BAD */` half while preserving exact
   Markdown line numbers, and an explicit `skip` reason. Every generated `.c` file ends with a
   non-empty typedef so comment-only blocks still satisfy `-Wpedantic`.
4. **Map.** Every compiler diagnostic is mapped back to `<markdown-path>:<markdown-line>`;
   build tools never have to read generated sources.

Usage:
    python scripts/check-examples.py [root] [--json] [--cc <compiler>] [--emit-dir <dir>]

Exit codes: 0 = every block compiles and the manifest is in sync, 1 = compile or manifest
error, 2 = no usable C compiler (or a usage/configuration error).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

# Markdown documents whose ```c blocks must compile. Evaluations are intentionally excluded.
DOC_GLOBS: Tuple[str, ...] = (
    "README.md",
    "CONTRIBUTING.md",
    "examples/*.md",
    "skills/*/SKILL.md",
    "skills/*/references/*.md",
)

MANIFEST_REL = Path("scripts") / "examples.json"

# Languages that select a C11 code block.
C_LANGS = frozenset({"c", "c11"})

# Appended to every generated translation unit so comment-only blocks are not empty TUs.
TU_TYPEDEF = "typedef int _examples_check_non_empty_tu_t;"

# The locked-door warning set from SKILL.md section 12. Compilation only checks syntax and
# semantics, so this is fast enough to run on every documentation edit.
BASE_FLAGS: Tuple[str, ...] = (
    "-std=c11",
    "-fsyntax-only",
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
    "-Wstrict-prototypes",
    "-Wold-style-definition",
    "-Wwrite-strings",
    "-Wcast-qual",
    "-Wvla",
    "-Wno-unused-function",
    "-Wno-unused-variable",
    "-Wno-unused-parameter",
)

# Purely cosmetic diagnostic-rendering flags. A compiler that rejects the first spelling gets
# the alias; if it rejects both, the flag is dropped instead of failing the gate.
COSMETIC_FLAG_ALIASES: Tuple[Tuple[str, Optional[str]], ...] = (
    ("-fno-diagnostics-show-caret", "-fno-caret-diagnostics"),
)

ALLOWED_MANIFEST_KEYS = frozenset({"prelude", "headers", "files"})
ALLOWED_FILE_KEYS = frozenset({"prelude", "blocks"})
ALLOWED_BLOCK_KEYS = frozenset(
    {"index", "first_line", "prelude", "template", "compile_from", "skip"}
)

FENCE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
DIAGNOSTIC_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?[ \t]*"
    r"(?P<severity>fatal error|error|warning|note):[ \t]*(?P<message>.*)$"
)

# "clang: error: unknown argument: '-foo'" / "gcc: error: unrecognized command-line option
# '-foo'" (gcc may wrap the option in typographic quotes).
REJECTED_FLAG_RE = re.compile(
    r"(?:unknown argument[s]?|unknown warning option|unrecognized command[- ]line option)"
    r"[:]?[ \t]*(?P<quote>['\"\u2018\u2019\u201c\u201d])?"
    r"(?P<flag>[^'\"\u2018\u2019\u201c\u201d \t]+)",
    re.IGNORECASE,
)
HEADER_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*\.h$")


class ConfigError(Exception):
    """The manifest, the harness, or the compiler environment is unusable."""


class BuildError(Exception):
    """A single code block cannot be turned into a translation unit."""


@dataclass(frozen=True)
class Problem:
    """A single actionable error, already located for the reader."""

    location: str
    message: str

    def render(self) -> str:
        return f"{self.location}: {self.message}"

    @classmethod
    def at(cls, path: str, line: int, message: str) -> "Problem":
        return cls(f"{path}:{line}" if line > 0 else path, message)

    @classmethod
    def in_manifest(cls, message: str) -> "Problem":
        return cls(MANIFEST_REL.as_posix(), message)


@dataclass(frozen=True)
class Block:
    """One top-level C code block extracted from a Markdown document."""

    path: str
    index: int
    fence_line: int
    start_line: int
    lines: Tuple[str, ...]
    first_line: str


@dataclass
class BlockResult:
    """Compilation outcome for one extracted block."""

    block: Block
    status: str  # "ok", "skipped", "failed", or "unharnessed"
    problems: List[Problem] = field(default_factory=list)
    skip_reason: str = ""


# --------------------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------------------


def iter_c_blocks(path: str, text: str) -> List[Block]:
    """Return every top-level ```c block in `text`, in document order.

    A fence is closed only by a fence of the same character with at least the same length and
    no info string, so a ```c block inside `~~~markdown` stays template content.
    """
    lines = text.splitlines()
    blocks: List[Block] = []
    open_char: Optional[str] = None
    open_len = 0
    open_lang = ""
    open_line = 0
    content: List[str] = []

    for lineno, line in enumerate(lines, start=1):
        match = FENCE_RE.match(line)
        if open_char is None:
            if match is None:
                continue
            fence = match.group("fence")
            info = match.group("info").strip()
            if fence[0] == "`" and "`" in info:
                continue  # not a valid opening fence
            open_char = fence[0]
            open_len = len(fence)
            open_lang = info.split()[0].lower() if info else ""
            open_line = lineno
            content = []
            continue

        is_close = (
            match is not None
            and match.group("fence")[0] == open_char
            and len(match.group("fence")) >= open_len
            and match.group("info").strip() == ""
        )
        if is_close:
            if open_lang in C_LANGS:
                first = next((item.strip() for item in content if item.strip()), "")
                blocks.append(
                    Block(
                        path=path,
                        index=len(blocks),
                        fence_line=open_line,
                        start_line=open_line + 1,
                        lines=tuple(content),
                        first_line=first,
                    )
                )
            open_char = None
            continue

        content.append(line)

    if open_char is not None and open_lang in C_LANGS:
        # Unterminated fence: still audit the block so the manifest stays truthful.
        first = next((item.strip() for item in content if item.strip()), "")
        blocks.append(
            Block(
                path=path,
                index=len(blocks),
                fence_line=open_line,
                start_line=open_line + 1,
                lines=tuple(content),
                first_line=first,
            )
        )
    return blocks


def discover_blocks(root: Path) -> Tuple[Dict[str, List[Block]], List[Problem]]:
    """Extract C blocks from every Markdown document matched by `DOC_GLOBS`."""
    documents = set()
    for pattern in DOC_GLOBS:
        for candidate in root.glob(pattern):
            if candidate.is_file():
                documents.add(candidate.relative_to(root).as_posix())

    blocks_by_file: Dict[str, List[Block]] = {}
    problems: List[Problem] = []
    for rel_path in sorted(documents):
        text = (root / rel_path).read_text(encoding="utf-8")
        blocks = iter_c_blocks(rel_path, text)
        for block in blocks:
            if not block.first_line:
                problems.append(
                    Problem.at(block.path, block.fence_line, "C code block is empty")
                )
        if blocks:
            blocks_by_file[rel_path] = blocks
    return blocks_by_file, problems


# --------------------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------------------


def _as_text(value: object, where: str) -> str:
    """Accept a string or a list of lines (joined with newlines) as harness text."""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "".join(line if line.endswith("\n") else line + "\n" for line in value)
    raise ConfigError(f"{where} must be a string or a list of strings")


def load_manifest(manifest_path: Path) -> Mapping[str, object]:
    """Read and structurally validate `scripts/examples.json`."""
    if not manifest_path.is_file():
        raise ConfigError(f"harness manifest not found: {manifest_path.as_posix()}")
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"{manifest_path.as_posix()} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigError("harness manifest must be a JSON object")

    unknown = {
        key
        for key in raw
        if key not in ALLOWED_MANIFEST_KEYS and not key.startswith("_")
    }
    if unknown:
        raise ConfigError(f"unknown manifest key(s): {', '.join(sorted(unknown))}")

    headers = raw.get("headers", {})
    if not isinstance(headers, dict):
        raise ConfigError("'headers' must be an object mapping file names to text")
    for name, body in headers.items():
        if not isinstance(name, str) or not HEADER_NAME_RE.match(name):
            raise ConfigError(f"invalid header name in 'headers': {name!r}")
        _as_text(body, f"headers[{name!r}]")

    files = raw.get("files", {})
    if not isinstance(files, dict):
        raise ConfigError("'files' must be an object keyed by Markdown path")
    for path, file_cfg in files.items():
        if not isinstance(file_cfg, dict):
            raise ConfigError(f"files[{path!r}] must be an object")
        unknown = set(file_cfg) - ALLOWED_FILE_KEYS
        if unknown:
            raise ConfigError(
                f"unknown key(s) in files[{path!r}]: {', '.join(sorted(unknown))}"
            )
        blocks = file_cfg.get("blocks", [])
        if not isinstance(blocks, list):
            raise ConfigError(f"files[{path!r}].blocks must be a list")
        for entry in blocks:
            if not isinstance(entry, dict):
                raise ConfigError(f"files[{path!r}].blocks entries must be objects")
            unknown = set(entry) - ALLOWED_BLOCK_KEYS
            if unknown:
                raise ConfigError(
                    f"unknown key(s) in a {path!r} block entry: "
                    f"{', '.join(sorted(unknown))}"
                )
            if not isinstance(entry.get("index"), int):
                raise ConfigError(
                    f"every block entry in {path!r} needs an integer 'index'"
                )
            if not isinstance(entry.get("first_line"), str):
                raise ConfigError(
                    f"every block entry in {path!r} needs a string 'first_line'"
                )
            for key in ("prelude", "template"):
                if entry.get(key) is not None:
                    _as_text(
                        entry[key], f"files[{path!r}].blocks[{entry['index']}].{key}"
                    )
            if entry.get("compile_from") is not None and not isinstance(
                entry["compile_from"], str
            ):
                raise ConfigError(
                    f"files[{path!r}].blocks[{entry['index']}].compile_from must be a string"
                )
            if entry.get("skip") is not None:
                reason = entry["skip"]
                if not isinstance(reason, str) or not reason.strip():
                    raise ConfigError(
                        f"files[{path!r}].blocks[{entry['index']}].skip needs a non-empty "
                        f"reason string"
                    )
        if file_cfg.get("prelude") is not None:
            _as_text(file_cfg["prelude"], f"files[{path!r}].prelude")
    if raw.get("prelude") is not None:
        _as_text(raw["prelude"], "prelude")
    return raw


def audit_manifest(
    manifest: Mapping[str, object], blocks_by_file: Mapping[str, List[Block]]
) -> Tuple[Dict[Tuple[str, int], Mapping[str, object]], List[Problem]]:
    """Cross-check the manifest against the discovered blocks, in both directions."""
    problems: List[Problem] = []
    cfg_by_block: Dict[Tuple[str, int], Mapping[str, object]] = {}
    files = manifest.get("files", {})
    assert isinstance(files, dict)

    for path, file_cfg in files.items():
        if path not in blocks_by_file:
            problems.append(
                Problem.in_manifest(
                    f"stale entry: {path!r} has no C code blocks (or no longer exists)"
                )
            )
            continue
        discovered = blocks_by_file[path]
        for entry in file_cfg.get("blocks", []):  # type: ignore[union-attr]
            index = entry["index"]
            key = (path, index)
            if index < 0 or index >= len(discovered):
                problems.append(
                    Problem.in_manifest(
                        f"{path}: block index {index} does not exist "
                        f"(the file has {len(discovered)} C block(s))"
                    )
                )
                continue
            if key in cfg_by_block:
                problems.append(
                    Problem.in_manifest(
                        f"{path}: duplicate entry for block index {index}"
                    )
                )
                continue
            block = discovered[index]
            expected = entry["first_line"].strip()
            if expected != block.first_line:
                problems.append(
                    Problem.at(
                        block.path,
                        block.start_line,
                        "harness drift: examples.json expects the block to start with "
                        f"{expected!r}, but the document starts with {block.first_line!r} "
                        "(update scripts/examples.json)",
                    )
                )
            cfg_by_block[key] = entry

    for path, discovered in blocks_by_file.items():
        for block in discovered:
            if (path, block.index) not in cfg_by_block:
                problems.append(
                    Problem.at(
                        block.path,
                        block.start_line,
                        f"unharnessed C code block {block.index}; add an entry with "
                        f"'index': {block.index} and 'first_line': "
                        f"{block.first_line!r} to scripts/examples.json",
                    )
                )
    return cfg_by_block, problems


# --------------------------------------------------------------------------------------
# Compiler discovery and flags
# --------------------------------------------------------------------------------------


def _resolvable(candidate: str) -> Optional[str]:
    """Resolve a compiler name or path the way a shell would, or return None."""
    if not candidate:
        return None
    found = shutil.which(candidate)
    if found:
        return found
    path = Path(candidate)
    if path.is_file():
        return str(path)
    return None


def resolve_compiler(explicit: Optional[str]) -> Optional[str]:
    """--cc -> $CC -> gcc -> clang -> cc, exactly as documented."""
    if explicit:
        return _resolvable(explicit)
    for candidate in (os.environ.get("CC", ""), "gcc", "clang", "cc"):
        found = _resolvable(candidate)
        if found:
            return found
    return None


def compiler_banner(cc: str) -> str:
    try:
        proc = subprocess.run(
            [cc, "--version"], capture_output=True, text=True, check=False
        )
    except OSError:
        return cc
    first = proc.stdout.splitlines()[0].strip() if proc.stdout else ""
    return f"{first} ({cc})" if first else cc


def _probe(cc: str, flags: Sequence[str], source: Path) -> Tuple[bool, str]:
    """Probe one flag combination; syntax-only mode keeps the probe link-free."""
    try:
        proc = subprocess.run(
            [cc, "-fsyntax-only", *flags, str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise ConfigError(f"cannot execute compiler {cc!r}: {exc}") from exc
    return proc.returncode == 0, "\n".join(
        part for part in (proc.stderr, proc.stdout) if part
    )


def rejected_flags(output: str) -> List[str]:
    """Collect the option names a compiler says it does not recognize."""
    return [match.group("flag") for match in REJECTED_FLAG_RE.finditer(output)]


def resolve_flags(
    cc: str, work_dir: Path
) -> Tuple[List[str], List[str], List[Problem]]:
    """Return (flags to use, dropped cosmetic flags, notes) for this compiler.

    The whole set is probed first. If the compiler rejects individual options, they are read
    back from its own diagnostic and the remainder is re-probed, so gcc gets
    `-fno-diagnostics-show-caret` and clang gets its `-fno-caret-diagnostics` spelling
    without one process launch per flag.
    """
    probe_source = work_dir / "probe.c"
    probe_source.write_text("typedef int _probe_non_empty_tu_t;\n", encoding="utf-8")

    ok, output = _probe(cc, [], probe_source)
    if not ok:
        raise ConfigError("compiler does not support the required -fsyntax-only mode")

    trial = list(BASE_FLAGS) + [alias for alias, _ in COSMETIC_FLAG_ALIASES]
    flags = list(trial)
    rejected: List[str] = []
    while True:
        ok, output = _probe(cc, flags, probe_source)
        if ok:
            break
        newly = [flag for flag in rejected_flags(output) if flag in flags]
        if not newly:
            # The failure is not an unknown option: identify offenders one flag at a time.
            newly = [flag for flag in flags if not _probe(cc, [flag], probe_source)[0]]
            if not newly:
                first_line = (
                    output.strip().splitlines()[0] if output.strip() else "no output"
                )
                raise ConfigError(f"compiler rejects the warning set: {first_line}")
        flags = [flag for flag in flags if flag not in newly]
        rejected.extend(newly)
        if not flags:
            raise ConfigError("compiler rejects every required warning flag")

    hard_failures = [flag for flag in rejected if flag in BASE_FLAGS]
    if hard_failures:
        raise ConfigError(
            "compiler does not support required flag(s): " + ", ".join(hard_failures)
        )

    dropped: List[str] = []
    notes: List[Problem] = []
    for flag, alias in COSMETIC_FLAG_ALIASES:
        if flag not in rejected:
            continue
        if alias and _probe(cc, [alias], probe_source)[0]:
            flags.append(alias)
            continue
        dropped.append(flag)
        notes.append(
            Problem(
                "compiler",
                f"{flag} is not supported by {Path(cc).name}; continuing without it",
            )
        )
    return flags, dropped, notes


# --------------------------------------------------------------------------------------
# Translation-unit construction
# --------------------------------------------------------------------------------------


def resolve_prelude(
    block: Block,
    entry: Mapping[str, object],
    file_cfg: Mapping[str, object],
    manifest: Mapping[str, object],
) -> str:
    """Per-block prelude overrides the per-file prelude, which overrides the global one."""
    if "prelude" in entry:
        return _as_text(entry["prelude"], f"{block.path}[{block.index}].prelude")
    if "prelude" in file_cfg:
        return _as_text(file_cfg["prelude"], f"{block.path} prelude")
    if "prelude" in manifest:
        return _as_text(manifest["prelude"], "global prelude")
    return ""


def build_translation_unit(
    block: Block, entry: Mapping[str, object], prelude: str
) -> Tuple[str, List[Optional[int]]]:
    """Build the generated `.c` text and a generated-line -> Markdown-line map."""
    code = list(block.lines)

    compile_from = entry.get("compile_from")
    if isinstance(compile_from, str) and compile_from:
        marker = next(
            (
                i
                for i, line in enumerate(code)
                if line.lstrip().startswith(compile_from)
            ),
            None,
        )
        if marker is None:
            raise BuildError(
                f"compile_from marker {compile_from!r} not found in the block"
            )
        for i in range(marker):
            code[i] = ""

    template = entry.get("template")
    if template is not None:
        template_text = _as_text(template, f"{block.path}[{block.index}].template")
        template_lines = template_text.splitlines()
        positions = [i for i, line in enumerate(template_lines) if "{code}" in line]
        if len(positions) != 1:
            raise BuildError("template must contain exactly one {code} placeholder")
        slot = positions[0]
        if template_lines[slot].strip() != "{code}":
            raise BuildError("the {code} placeholder must sit on its own template line")
        body = template_lines[:slot] + code + template_lines[slot + 1 :]
        mapping: List[Optional[int]] = (
            [None] * slot
            + list(range(block.start_line, block.start_line + len(code)))
            + [None] * (len(template_lines) - slot - 1)
        )
    else:
        body = code
        mapping = list(range(block.start_line, block.start_line + len(code)))

    prelude_lines = prelude.splitlines() if prelude else []
    source = "\n".join(prelude_lines + body + ["", TU_TYPEDEF]) + "\n"
    line_map: List[Optional[int]] = [None] * len(prelude_lines) + mapping + [None, None]
    return source, line_map


def generated_name(block: Block) -> str:
    stem = block.path.replace("/", "_").replace(".", "_")
    return f"{stem}_{block.index:02d}.c"


def map_diagnostics(
    block: Block,
    output: str,
    source_name: str,
    line_map: Sequence[Optional[int]],
) -> List[Problem]:
    """Translate compiler diagnostics into `<markdown-path>:<markdown-line>` problems.

    `note:` lines are folded into the preceding finding instead of being counted as errors.
    """
    located: List[List[str]] = []  # [location, message]
    loose: List[str] = []
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = DIAGNOSTIC_RE.match(line)
        if match is None:
            loose.append(line.strip())
            continue
        severity = match.group("severity")
        message = match.group("message").strip()
        file_text = match.group("file")

        if severity == "note":
            if located:
                located[-1][1] += f" ({message})"
            continue

        if Path(file_text).name != source_name:
            header = Path(file_text).name + ":" + match.group("line")
            harness_note = f"[harness] {header}: {severity}: {message}"
            located.append([f"{block.path}:{block.fence_line}", harness_note])
            continue

        generated_line = int(match.group("line"))
        markdown_line = (
            line_map[generated_line - 1]
            if 1 <= generated_line <= len(line_map)
            else None
        )
        if markdown_line is None:
            located.append(
                [
                    f"{block.path}:{block.fence_line}",
                    f"[harness/template] {severity}: {message}",
                ]
            )
        else:
            located.append([f"{block.path}:{markdown_line}", f"{severity}: {message}"])

    problems = [Problem(location, message) for location, message in located]
    for line in loose:
        problems.append(Problem.at(block.path, block.fence_line, f"[compiler] {line}"))
    if not problems:
        problems.append(
            Problem.at(
                block.path,
                block.fence_line,
                "compiler failed with no parseable diagnostic (exit code != 0)",
            )
        )
    return problems


def compile_block(
    cc: str,
    flags: Sequence[str],
    include_dir: Path,
    work_dir: Path,
    emit_dir: Optional[Path],
    block: Block,
    entry: Mapping[str, object],
    prelude: str,
) -> BlockResult:
    """Build and compile one block, returning a located result."""
    skip_reason = entry.get("skip")
    if isinstance(skip_reason, str) and skip_reason.strip():
        return BlockResult(
            block=block, status="skipped", skip_reason=skip_reason.strip()
        )

    try:
        source, line_map = build_translation_unit(block, entry, prelude)
    except BuildError as exc:
        return BlockResult(
            block=block,
            status="failed",
            problems=[Problem.at(block.path, block.fence_line, str(exc))],
        )

    name = generated_name(block)
    source_path = work_dir / name
    source_path.write_text(source, encoding="utf-8")
    if emit_dir is not None:
        emit_dir.mkdir(parents=True, exist_ok=True)
        (emit_dir / name).write_text(source, encoding="utf-8")

    proc = subprocess.run(
        [cc, *flags, f"-I{include_dir.as_posix()}", str(source_path)],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(work_dir),
    )
    if proc.returncode == 0:
        return BlockResult(block=block, status="ok")
    output = "\n".join(part for part in (proc.stderr, proc.stdout) if part)
    return BlockResult(
        block=block,
        status="failed",
        problems=map_diagnostics(block, output, name, line_map),
    )


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------


def materialize_headers(manifest: Mapping[str, object], include_dir: Path) -> List[str]:
    """Write every declared header into `<tmp>/include` and return the sorted names."""
    headers = manifest.get("headers", {})
    assert isinstance(headers, dict)
    include_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    for name in sorted(headers):
        text = _as_text(headers[name], f"headers[{name!r}]")
        if text and not text.endswith("\n"):
            text += "\n"
        destination = include_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        written.append(name)
    return written


def run_gate(args: argparse.Namespace) -> int:
    root = (
        Path(args.root).resolve()
        if args.root
        else Path(__file__).resolve().parent.parent
    )
    manifest_path = root / MANIFEST_REL

    try:
        manifest = load_manifest(manifest_path)
    except ConfigError as exc:
        print(f"[CONFIG ERROR] {exc}", file=sys.stderr)
        return 2

    blocks_by_file, problems = discover_blocks(root)
    if not blocks_by_file:
        print(
            f"[CONFIG ERROR] no C code blocks matched {DOC_GLOBS!r} under "
            f"{root.as_posix()}; is that the repository root?",
            file=sys.stderr,
        )
        return 2
    cfg_by_block, sync_problems = audit_manifest(manifest, blocks_by_file)
    problems.extend(sync_problems)

    cc = resolve_compiler(args.cc)
    if cc is None:
        hint = (
            f"--cc {args.cc!r} is not an executable"
            if args.cc
            else "install gcc or clang, set $CC, or pass --cc <compiler>"
        )
        print(f"[NO COMPILER] no C compiler found ({hint}).", file=sys.stderr)
        return 2

    total_blocks = sum(len(blocks) for blocks in blocks_by_file.values())
    emit_dir = Path(args.emit_dir).resolve() if args.emit_dir else None

    results: List[BlockResult] = []
    notes: List[Problem] = []
    harness_headers: List[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="bec_examples_") as tmp:
            work_dir = Path(tmp)
            include_dir = work_dir / "include"
            flags, _dropped, flag_notes = resolve_flags(cc, work_dir)
            notes.extend(flag_notes)
            harness_headers = materialize_headers(manifest, include_dir)
            files_cfg = manifest.get("files", {})
            assert isinstance(files_cfg, dict)

            for path in sorted(blocks_by_file):
                file_cfg = files_cfg.get(path, {})
                assert isinstance(file_cfg, dict)
                for block in blocks_by_file[path]:
                    entry = cfg_by_block.get((path, block.index))
                    if entry is None:
                        results.append(BlockResult(block=block, status="unharnessed"))
                        continue
                    prelude = resolve_prelude(block, entry, file_cfg, manifest)
                    results.append(
                        compile_block(
                            cc,
                            flags,
                            include_dir,
                            work_dir,
                            emit_dir,
                            block,
                            entry,
                            prelude,
                        )
                    )
    except ConfigError as exc:
        print(f"[CONFIG ERROR] {exc}", file=sys.stderr)
        return 2

    for result in results:
        problems.extend(result.problems)

    return report(
        args=args,
        root=root,
        cc=cc,
        header_names=harness_headers,
        blocks_by_file=blocks_by_file,
        results=results,
        problems=problems,
        notes=notes,
        total_blocks=total_blocks,
    )


def report(
    args: argparse.Namespace,
    root: Path,
    cc: str,
    header_names: Sequence[str],
    blocks_by_file: Mapping[str, List[Block]],
    results: Sequence[BlockResult],
    problems: Sequence[Problem],
    notes: Sequence[Problem],
    total_blocks: int,
) -> int:
    """Print the human or JSON report and return the exit status."""
    compiled = sum(1 for item in results if item.status == "ok")
    skipped = sum(1 for item in results if item.status == "skipped")
    failed = sum(1 for item in results if item.status == "failed")
    unharnessed = sum(1 for item in results if item.status == "unharnessed")

    if args.json:
        status_by_block = {
            (item.block.path, item.block.index): item.status for item in results
        }
        payload = {
            "root": root.as_posix(),
            "compiler": cc,
            "headers": list(header_names),
            "files": [
                {
                    "path": path,
                    "blocks": [
                        {
                            "index": block.index,
                            "start_line": block.start_line,
                            "first_line": block.first_line,
                            "status": status_by_block.get(
                                (path, block.index), "unharnessed"
                            ),
                        }
                        for block in blocks
                    ],
                }
                for path, blocks in sorted(blocks_by_file.items())
            ],
            "problems": [
                {"location": item.location, "message": item.message}
                for item in problems
            ],
            "summary": {
                "files": len(blocks_by_file),
                "blocks": total_blocks,
                "compiled": compiled,
                "skipped": skipped,
                "failed": failed,
                "unharnessed": unharnessed,
                "errors": len(problems),
            },
        }
        print(json.dumps(payload, indent=2, sort_keys=False))
        return 0 if not problems else 1

    print("BeautifulEmbeddedC example compile gate")
    print(f"  root:     {root.as_posix()}")
    print(f"  compiler: {compiler_banner(cc)}")
    print(f"  harness:  {len(header_names)} header(s) from {MANIFEST_REL.as_posix()}")
    print(
        f"  blocks:   {total_blocks} C code block(s) in "
        f"{len(blocks_by_file)} Markdown document(s)"
    )
    print()

    for item in results:
        block = item.block
        if item.status == "ok":
            print(f"[OK]   {block.path}:{block.start_line} (block {block.index})")
        elif item.status == "skipped":
            print(
                f"[SKIP] {block.path}:{block.start_line} (block {block.index}): "
                f"{item.skip_reason}"
            )

    if notes:
        print()
        for note in notes:
            print(f"[NOTE] {note.render()}")

    if problems:
        print()
        for problem in problems:
            print(f"ERROR: {problem.render()}", file=sys.stderr)
        print()

    print(
        f"{total_blocks} block(s): {compiled} compiled, {skipped} skipped, "
        f"{failed} failed, {unharnessed} unharnessed; {len(problems)} error(s)."
    )
    if problems:
        print("[EXAMPLES CHECK FAILED]", file=sys.stderr)
        return 1
    print("[EXAMPLES CHECK PASSED]")
    return 0


def parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compile every C11 code block in the documentation with the strict warning set "
            "and verify that scripts/examples.json is in sync."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="repository root (default: the parent directory of scripts/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable JSON report on stdout",
    )
    parser.add_argument(
        "--cc",
        default=None,
        help="C compiler to use (default: $CC, then gcc, then clang, then cc)",
    )
    parser.add_argument(
        "--emit-dir",
        default=None,
        help="optional directory that keeps the generated .c files for inspection",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run_gate(parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
