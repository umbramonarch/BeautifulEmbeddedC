"""Unit tests for ``scripts/check-skill.py`` using synthetic repositories.

Run with::

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check-skill.py"


def _load_check_skill() -> Any:
    spec = importlib.util.spec_from_file_location("check_skill", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_skill = _load_check_skill()

SKILL_DIR = "embedded-c-best-practices"
CASE_DIR = "case-one"

PLUGIN_JSON = {
    "name": "test-plugin",
    "version": "1.0.0",
    "description": "A synthetic plugin used by the validator unit tests.",
    "license": "MIT",
}
MARKETPLACE_JSON = {
    "name": "test-plugin",
    "owner": {"name": "tester"},
    "plugins": [{"name": "test-plugin", "source": "./"}],
}
CHANGELOG = """# Changelog

All notable changes to this project are listed here.

## [Unreleased]

## [1.0.0] - 2026-01-01

### Added

- Initial synthetic release.

[Unreleased]: https://example.com/compare/v1.0.0...HEAD
[1.0.0]: https://example.com/releases/tag/v1.0.0
"""
README = """# Synthetic Embedded C

See the [writing skill](skills/embedded-c-best-practices/SKILL.md) and the
[license](LICENSE).
"""
CONTRIBUTING = """# Contributing

Read the [license](LICENSE) before you open a pull request.
"""
SKILL_MD = """---
name: embedded-c-best-practices
description: >-
  Write deterministic, testable, safety-critical Embedded C. Use this skill whenever you
  write, review, or refactor firmware, and cite the rule IDs it defines.
license: MIT
compatibility: Works with any agent that reads the Agent Skills format.
metadata:
  author: synthetic
allowed-tools: [Read, Write]
---

# Embedded C best practices

Load the digest at `references/nasa.md` when a task needs the NASA JPL rules.

## Rules

Follow `[JPL-1]` and `[JPL-2]` in every production `.c` file.
"""
NASA_REFERENCE = """# NASA JPL Power of 10

### `[JPL-1]` Simple, acyclic control flow

### `[JPL-2]` Fixed upper bounds on every loop
"""
PROMPT_MD = """---
tags: [embedded-c-best-practices]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Write, Bash]
---

Write a small ring buffer library and a host unit test.
"""
CASE_YAML = """schema_version: "1.1"
name: case-one
context:
  scaffold_script: place-files.sh
expected_outcome: |
  A valid synthetic outcome used by the validator unit tests.
"""
GRADER_MD = """---
type: llm
focus: safety
weight: 1
---

The generated module bounds every hardware polling loop with a timeout counter.
"""
PLACE_FILES = """#!/usr/bin/env bash
set -eu
cp -R "$(dirname "$0")/files/." .
"""
SAMPLE_EXAMPLE = """# Sample review

The reviewer cites `[JPL-1]` and `[JPL-2]` in the findings table.
"""
CHECK_ARCH = '''#!/usr/bin/env python3
"""Synthetic architecture gate citing `[JPL-2]` in its docstring."""
'''


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def build_repo(root: Path) -> Path:
    """Create a minimal, completely valid synthetic repository."""
    write_text(root / ".claude-plugin" / "plugin.json", json.dumps(PLUGIN_JSON, indent=2))
    write_text(
        root / ".claude-plugin" / "marketplace.json",
        json.dumps(MARKETPLACE_JSON, indent=2),
    )
    write_text(root / "CHANGELOG.md", CHANGELOG)
    write_text(root / "README.md", README)
    write_text(root / "CONTRIBUTING.md", CONTRIBUTING)
    write_text(root / "LICENSE", "MIT License\n")
    skill_dir = root / "skills" / SKILL_DIR
    write_text(skill_dir / "SKILL.md", SKILL_MD)
    write_text(skill_dir / "references" / "nasa.md", NASA_REFERENCE)
    case_dir = skill_dir / "evals" / CASE_DIR
    write_text(case_dir / "case.yaml", CASE_YAML)
    write_text(case_dir / "prompt.md", PROMPT_MD)
    write_text(case_dir / "place-files.sh", PLACE_FILES)
    write_text(case_dir / "files" / "motor.c", "int main(void) { return 0; }\n")
    write_text(case_dir / "graders" / "01-bounded-loop.md", GRADER_MD)
    write_text(case_dir / "graders" / "02-checked-returns.md", GRADER_MD)
    write_text(root / "examples" / "sample.md", SAMPLE_EXAMPLE)
    write_text(root / "lints" / "check_arch.py", CHECK_ARCH)
    return skill_dir


class RepoTestCase(unittest.TestCase):
    """Base class that builds a valid synthetic repository per test."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skill_dir = build_repo(self.root)
        self.skill_md = self.skill_dir / "SKILL.md"
        self.case_dir = self.skill_dir / "evals" / CASE_DIR

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def problems(self) -> List[Any]:
        return check_skill.check_repo(self.root)

    def errors(self) -> List[Any]:
        return [p for p in self.problems() if p.level == "error"]

    def warnings(self) -> List[Any]:
        return [p for p in self.problems() if p.level == "warning"]

    def messages(self) -> str:
        return "\n".join("%s:%d: %s" % (p.path, p.line, p.message) for p in self.problems())

    def run_main(self, *args: str) -> int:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = check_skill.main([str(self.root), *args])
        self.last_stdout = buffer.getvalue()
        return code

    def write_skill(self, text: str) -> None:
        write_text(self.skill_md, text)

    def write_marketplace(self, data: Dict[str, Any]) -> None:
        write_text(
            self.root / ".claude-plugin" / "marketplace.json",
            json.dumps(data, indent=2),
        )

    def write_skill_with_body(self, body: str) -> None:
        frontmatter = SKILL_MD.split("---\n")[1]
        trailer = "\nSee `references/nasa.md` for the digests.\n"
        self.write_skill("---\n" + frontmatter + "---\n\n" + body + trailer)

    def assert_error_contains(self, needle: str) -> None:
        joined = self.messages()
        self.assertIn(
            needle,
            joined,
            "expected an error containing %r in:\n%s" % (needle, joined),
        )


class ValidRepositoryTests(RepoTestCase):
    def test_valid_repository_has_no_problems(self) -> None:
        problems = self.problems()
        self.assertEqual(len(problems), 0, self.messages())

    def test_exit_code_is_zero_without_errors(self) -> None:
        self.assertEqual(self.run_main(), 0)

    def test_body_line_warning_keeps_exit_code_zero(self) -> None:
        body = "# Long skill\n\n" + ("Filler guidance line.\n" * 520)
        self.write_skill_with_body(body)
        levels = {p.level for p in self.problems()}
        self.assertIn("warning", levels)
        self.assertEqual(self.errors(), [], self.messages())
        self.assertEqual(self.run_main(), 0)
        self.assertIn("SKILL.md body has", self.last_stdout)


class SkillFrontmatterTests(RepoTestCase):
    def test_skill_name_must_be_kebab_case(self) -> None:
        self.write_skill(
            SKILL_MD.replace("name: embedded-c-best-practices", "name: Embedded_C")
        )
        self.assert_error_contains("must be lowercase letters, digits, and hyphens")

    def test_skill_name_must_match_folder(self) -> None:
        other = self.root / "skills" / "other-skill"
        write_text(
            other / "SKILL.md",
            SKILL_MD.replace("embedded-c-best-practices", "wrong-name"),
        )
        self.assert_error_contains("must equal the folder name 'other-skill'")

    def test_skill_name_too_long(self) -> None:
        long_name = "a" * 70
        folder = self.root / "skills" / long_name
        write_text(
            folder / "SKILL.md",
            SKILL_MD.replace("embedded-c-best-practices", long_name),
        )
        self.assert_error_contains("name exceeds 64 characters")

    def test_missing_description(self) -> None:
        lines = [line for line in SKILL_MD.splitlines() if not line.startswith("description:")]
        lines = [line for line in lines if not line.startswith("  Write deterministic")]
        lines = [line for line in lines if not line.startswith("  write, review")]
        self.write_skill("\n".join(lines) + "\n")
        self.assert_error_contains("missing description")

    def test_description_too_long(self) -> None:
        self.write_skill(
            SKILL_MD.replace(
                "  Write deterministic, testable, safety-critical Embedded C. Use this "
                "skill whenever you\n  write, review, or refactor firmware, and cite the "
                "rule IDs it defines.",
                "  " + ("x" * 1100),
            )
        )
        self.assert_error_contains("description exceeds 1024 characters")

    def test_unknown_frontmatter_key(self) -> None:
        self.write_skill(SKILL_MD.replace("license: MIT", "license: MIT\nunexpected: true"))
        self.assert_error_contains("unknown frontmatter key: unexpected")

    def test_compatibility_too_long(self) -> None:
        self.write_skill(
            SKILL_MD.replace(
                "compatibility: Works with any agent that reads the Agent Skills format.",
                "compatibility: " + ("y" * 600),
            )
        )
        self.assert_error_contains("compatibility exceeds 500 characters")

    def test_missing_frontmatter_block(self) -> None:
        self.write_skill("# No frontmatter here\n")
        self.assert_error_contains("missing YAML frontmatter")

    def test_body_over_500_lines_is_only_a_warning(self) -> None:
        self.write_skill_with_body("# Skill\n\n" + ("rule line\n" * 505))
        warnings = self.warnings()
        self.assertTrue(warnings, self.messages())
        self.assertEqual(warnings[0].level, "warning")
        self.assertEqual(self.errors(), [], self.messages())


class LinkTests(RepoTestCase):
    def test_broken_readme_link(self) -> None:
        write_text(self.root / "README.md", README + "\nSee [missing](docs/missing.md).\n")
        self.assert_error_contains("broken link docs/missing.md")

    def test_broken_contributing_link(self) -> None:
        write_text(self.root / "CONTRIBUTING.md", CONTRIBUTING + "\n[Docs](docs/nope.md)\n")
        self.assert_error_contains("broken link docs/nope.md")

    def test_broken_reference_mention_in_skill(self) -> None:
        self.write_skill(SKILL_MD + "\nAlso read `references/ghost.md`.\n")
        self.assert_error_contains("broken link references/ghost.md")

    def test_orphan_reference_is_reported(self) -> None:
        write_text(self.skill_dir / "references" / "orphan.md", "# Orphan\n")
        self.assert_error_contains("orphan reference references/orphan.md")

    def test_sibling_skill_can_use_shared_references(self) -> None:
        other = self.root / "skills" / "other-skill"
        write_text(
            other / "SKILL.md",
            "---\nname: other-skill\ndescription: Another synthetic skill.\n---\n\n"
            "Load `references/nasa.md` for the JPL rules.\n",
        )
        self.assertNotIn("broken link references/nasa.md", self.messages())
        self.assertEqual(self.errors(), [], self.messages())

    def test_link_resolves_through_shared_reference_directory(self) -> None:
        other = self.root / "skills" / "other-skill"
        write_text(
            other / "SKILL.md",
            "---\nname: other-skill\ndescription: Another synthetic skill.\n---\n\n"
            "Load [the digest](references/nasa.md) first.\n",
        )
        self.assertNotIn("broken link references/nasa.md", self.messages())
        self.assertEqual(self.errors(), [], self.messages())


class EvalCaseTests(RepoTestCase):
    def test_grader_numbers_must_be_contiguous(self) -> None:
        graders = self.case_dir / "graders"
        (graders / "02-checked-returns.md").rename(graders / "03-checked-returns.md")
        self.assert_error_contains("grader numbers are not contiguous")

    def test_grader_filename_must_be_numbered(self) -> None:
        write_text(self.case_dir / "graders" / "grader-three.md", GRADER_MD)
        self.assert_error_contains("grader filename must be NN-slug.md")

    def test_grader_missing_frontmatter(self) -> None:
        write_text(
            self.case_dir / "graders" / "02-checked-returns.md",
            "The module checks every status return.\n",
        )
        self.assert_error_contains("missing YAML frontmatter")

    def test_grader_missing_required_key(self) -> None:
        write_text(
            self.case_dir / "graders" / "02-checked-returns.md",
            "---\ntype: llm\nweight: 1\n---\n\nA checkable assertion.\n",
        )
        self.assert_error_contains("missing focus")

    def test_grader_empty_body(self) -> None:
        write_text(
            self.case_dir / "graders" / "02-checked-returns.md",
            "---\ntype: llm\nfocus: safety\nweight: 1\n---\n",
        )
        self.assert_error_contains("grader body is empty")

    def test_empty_graders_directory(self) -> None:
        graders = self.case_dir / "graders"
        for child in graders.iterdir():
            child.unlink()
        self.assert_error_contains("no grader files")

    def test_prompt_requires_frontmatter(self) -> None:
        write_text(self.case_dir / "prompt.md", "Do the thing with no frontmatter.\n")
        self.assert_error_contains("missing YAML frontmatter")

    def test_prompt_requires_tags(self) -> None:
        write_text(
            self.case_dir / "prompt.md",
            "---\nmax_turns: 30\ntimeout_seconds: 900\n---\n\nDo the thing.\n",
        )
        self.assert_error_contains("missing tags")

    def test_prompt_rejects_empty_tag_list(self) -> None:
        write_text(
            self.case_dir / "prompt.md",
            "---\ntags: []\nmax_turns: 30\ntimeout_seconds: 900\n---\n\nDo the thing.\n",
        )
        self.assert_error_contains("missing tags")

    def test_case_yaml_name_must_match_folder(self) -> None:
        write_text(
            self.case_dir / "case.yaml",
            CASE_YAML.replace("name: case-one", "name: other"),
        )
        self.assert_error_contains("must equal the folder name 'case-one'")

    def test_case_yaml_requires_expected_outcome(self) -> None:
        text = "\n".join(
            line
            for line in CASE_YAML.splitlines()
            if not line.startswith(("expected_outcome", "  A valid synthetic"))
        )
        write_text(self.case_dir / "case.yaml", text + "\n")
        self.assert_error_contains("missing expected_outcome")

    def test_missing_graders_directory(self) -> None:
        graders = self.case_dir / "graders"
        for child in graders.iterdir():
            child.unlink()
        graders.rmdir()
        self.assert_error_contains("missing graders directory")

    def test_place_files_referenced_file_missing(self) -> None:
        write_text(
            self.case_dir / "place-files.sh",
            "#!/usr/bin/env bash\nset -eu\ncp files/motor_ctrl.c files/motor_ctrl.h .\n",
        )
        self.assert_error_contains("references files/motor_ctrl.c, which does not exist")

    def test_place_files_missing_files_directory(self) -> None:
        files_dir = self.case_dir / "files"
        for child in files_dir.iterdir():
            child.unlink()
        files_dir.rmdir()
        write_text(
            self.case_dir / "place-files.sh",
            "#!/usr/bin/env bash\nset -eu\ncp files/motor_ctrl.c .\n",
        )
        self.assert_error_contains("missing files/ directory")

    def test_place_files_script_required_by_case_yaml(self) -> None:
        (self.case_dir / "place-files.sh").unlink()
        self.assert_error_contains("place-files.sh:1: missing file")

    def test_scaffold_script_from_context_must_exist(self) -> None:
        write_text(
            self.case_dir / "case.yaml",
            CASE_YAML.replace("scaffold_script: place-files.sh", "scaffold_script: setup.sh"),
        )
        self.assert_error_contains("setup.sh:1: missing file")

    def test_scaffold_script_files_are_validated(self) -> None:
        write_text(
            self.case_dir / "case.yaml",
            CASE_YAML.replace("scaffold_script: place-files.sh", "scaffold_script: setup.sh"),
        )
        write_text(
            self.case_dir / "setup.sh",
            "#!/usr/bin/env bash\nset -eu\ncp files/present.txt files/absent.h .\n",
        )
        write_text(self.case_dir / "files" / "present.txt", "present\n")
        self.assert_error_contains("references files/absent.h, which does not exist")


class RuleSynchronizationTests(RepoTestCase):
    def test_unknown_rule_id_in_skill_errors(self) -> None:
        self.write_skill(SKILL_MD + "\nAlso obey `[JPL-99]`.\n")
        self.assert_error_contains("unknown rule ID [JPL-99]")

    def test_unknown_rule_id_in_examples_errors(self) -> None:
        write_text(
            self.root / "examples" / "sample.md",
            SAMPLE_EXAMPLE + "\n**Rule:** `[BARR-99.9]`.\n",
        )
        self.assert_error_contains("unknown rule ID [BARR-99.9]")

    def test_unknown_rule_id_in_check_arch_errors(self) -> None:
        write_text(
            self.root / "lints" / "check_arch.py",
            CHECK_ARCH + "\n# Enforces [MISRA-99.9].\n",
        )
        self.assert_error_contains("unknown rule ID [MISRA-99.9]")

    def test_rule_defined_in_reference_digest_is_accepted(self) -> None:
        self.skill_md.write_text(SKILL_MD + "\nAlso `[JPL-2]`.\n", encoding="utf-8")
        self.assertEqual(self.errors(), [], self.messages())

    def test_placeholder_rule_ids_are_skipped(self) -> None:
        write_text(
            self.skill_dir / "references" / "template.md",
            "# Template\n\nUse `[RULE-ID]` or `[SOURCE-ID]` as a placeholder.\n",
        )
        self.write_skill(SKILL_MD + "\nMention `references/template.md` and `[RULE-ID]`.\n")
        self.assertEqual(self.errors(), [], self.messages())

    def test_rule_ranges_with_ellipsis_are_skipped(self) -> None:
        self.write_skill(SKILL_MD + "\nSee `[BENINGO-ARCH-01..03]` for the layers.\n")
        self.assertEqual(self.errors(), [], self.messages())


class ManifestAndChangelogTests(RepoTestCase):
    def test_missing_plugin_json(self) -> None:
        (self.root / ".claude-plugin" / "plugin.json").unlink()
        self.assert_error_contains("plugin.json:1: missing file")

    def test_non_semver_version(self) -> None:
        data = dict(PLUGIN_JSON, version="1.0")
        write_text(self.root / ".claude-plugin" / "plugin.json", json.dumps(data, indent=2))
        self.assert_error_contains("version '1.0' is not semver")

    def test_marketplace_name_mismatch(self) -> None:
        data = dict(MARKETPLACE_JSON, name="other-marketplace")
        self.write_marketplace(data)
        self.assert_error_contains("marketplace name 'other-marketplace' does not match")

    def test_marketplace_plugin_entry_mismatch(self) -> None:
        data = dict(MARKETPLACE_JSON, plugins=[{"name": "other-plugin", "source": "./"}])
        self.write_marketplace(data)
        self.assert_error_contains("does not match 'test-plugin' in plugin.json")

    def test_changelog_must_reference_released_version(self) -> None:
        write_text(
            self.root / "CHANGELOG.md",
            CHANGELOG.replace("## [1.0.0] - 2026-01-01", "## [0.9.0] - 2025-01-01").replace(
                "[1.0.0]: https://example.com/releases/tag/v1.0.0",
                "[0.9.0]: https://example.com/releases/tag/v0.9.0",
            ).replace("compare/v1.0.0...HEAD", "compare/v0.9.0...HEAD"),
        )
        self.assert_error_contains("does not reference version 1.0.0")

    def test_changelog_missing_unreleased_link(self) -> None:
        write_text(
            self.root / "CHANGELOG.md",
            CHANGELOG.replace(
                "[Unreleased]: https://example.com/compare/v1.0.0...HEAD",
                "[Unreleased]: https://example.com/commits",
            ),
        )
        self.assert_error_contains("does not reference version 1.0.0")

    def test_changelog_missing_section(self) -> None:
        write_text(self.root / "CHANGELOG.md", "# Changelog\n\nNothing yet.\n")
        self.assert_error_contains("needs an [Unreleased] section")


class JsonAndExitCodeTests(RepoTestCase):
    def test_json_output_reports_problems(self) -> None:
        write_text(self.root / "README.md", README + "\n[gone](docs/gone.md)\n")
        code = self.run_main("--json")
        self.assertEqual(code, 1)
        data: Dict[str, Any] = json.loads(self.last_stdout)
        self.assertFalse(data["ok"])
        self.assertGreaterEqual(data["error_count"], 1)
        self.assertEqual(data["error_count"], len(data["problems"]))
        self.assertIn("error", data["summary"])
        first = data["problems"][0]
        self.assertEqual(set(first), {"path", "line", "level", "message"})
        self.assertTrue(
            any("broken link docs/gone.md" in p["message"] for p in data["problems"])
        )

    def test_json_output_ok_for_clean_repo(self) -> None:
        self.assertEqual(self.run_main("--json"), 0)
        data = json.loads(self.last_stdout)
        self.assertTrue(data["ok"])
        self.assertEqual(data["error_count"], 0)
        self.assertEqual(data["problems"], [])

    def test_missing_root_path_exits_one(self) -> None:
        missing = str(self.root / "does-not-exist")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = check_skill.main([missing])
        self.assertEqual(code, 1)
        self.assertIn("path does not exist", buffer.getvalue())


class YamlParserTests(unittest.TestCase):
    def test_flow_sequences_and_maps(self) -> None:
        data, _ = check_skill.parse_yaml(
            'tags: [alpha, "beta, gamma"]\nmetadata: {owner: tester, weight: 1}\n'
        )
        self.assertEqual(data["tags"], ["alpha", "beta, gamma"])
        self.assertEqual(data["metadata"], {"owner": "tester", "weight": 1})

    def test_block_scalar_styles(self) -> None:
        text = textwrap.dedent(
            """\
            literal: |
              line one
              line two
            folded: >-
              line one
              line two
            stripped: |-
              no newline
            kept: |+
              kept

            """
        )
        data, _ = check_skill.parse_yaml(text)
        self.assertEqual(data["literal"], "line one\nline two\n")
        self.assertEqual(data["folded"], "line one line two")
        self.assertEqual(data["stripped"], "no newline")
        self.assertTrue(data["kept"].startswith("kept"))

    def test_nested_sequences(self) -> None:
        data, locs = check_skill.parse_yaml(
            "context:\n  scaffold_script: place-files.sh\nplugins:\n  - one\n  - two\n"
        )
        self.assertEqual(data["context"]["scaffold_script"], "place-files.sh")
        self.assertEqual(data["plugins"], ["one", "two"])
        self.assertEqual(locs[("plugins", "0")], 4)

    def test_quoted_scalars_and_escapes(self) -> None:
        data, _ = check_skill.parse_yaml('a: "line\\nbreak"\nb: \'It\'\'s ok\'\n')
        self.assertEqual(data["a"], "line\nbreak")
        self.assertEqual(data["b"], "It's ok")

    def test_tab_indentation_is_rejected(self) -> None:
        with self.assertRaises(check_skill.YamlError):
            check_skill.parse_yaml("key:\n\tsub: 1\n")

    def test_unterminated_quote_is_rejected(self) -> None:
        with self.assertRaises(check_skill.YamlError):
            check_skill.parse_yaml('name: "oops\n')

    def test_line_numbers_are_reported(self) -> None:
        _, locs = check_skill.parse_yaml("alpha: 1\nbeta:\n  gamma: 2\n")
        self.assertEqual(locs[("alpha",)], 1)
        self.assertEqual(locs[("beta", "gamma")], 3)

    def test_split_frontmatter_returns_body_start(self) -> None:
        frontmatter, body, body_start = check_skill.split_frontmatter(
            "---\nname: x\n---\n\n# Body\n"
        )
        self.assertEqual(frontmatter, "name: x\n")
        self.assertEqual(body, "\n# Body\n")
        self.assertEqual(body_start, 4)


if __name__ == "__main__":
    unittest.main()
