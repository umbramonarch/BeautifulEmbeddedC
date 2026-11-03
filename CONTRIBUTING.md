# Contributing

Thanks for helping make Beautiful Embedded C better. Issues and pull requests are welcome.
A few conventions keep the skills consistent, vendor-neutral, and trustworthy for the
agents that load them mid-task.

## The one rule: every rule needs a source

The skills are a synthesis of published Embedded C guidance, not a list of opinions. Every
rule you add or change should trace back to one of the five authorities the repository is
built on, or to a source of similar weight:

- **Jacob Beningo, *Reusable Firmware Development*** — the four-layer `app` / `bsp` /
  `config` / `drv` architecture, pure vertical `libs/`, vendor-free public headers, and
  `const` configuration tables that live in `.rodata` Flash.
- **James Grenning, *Test-Driven Development for Embedded C*** — dual-target host/target
  compilation, link-time substitution with fakes and spies instead of `#ifdef TEST`,
  the Humble Object pattern, and opaque handles for automatic data types.
- **Gerard Holzmann, *NASA JPL Power of 10*** — simple acyclic control flow, fixed upper
  bounds on every loop, zero dynamic allocation, functions of 60 lines or fewer, and a
  clean build at maximum compiler warning levels.
- **Michael Barr, *BARR-C:2018 Embedded C Coding Standard*** — module-prefixed naming,
  physical unit suffixes (`_mv`, `_ma`, `_hz`, `_ms`), fixed-width `<stdint.h>` types,
  mandatory braces, and `const` / `volatile` discipline.
- **MISRA C Essential Type Model** — zero implicit sign or float conversions, single-field
  unit wrapper structs, and compile-time `_Static_assert` proofs of configuration tables.

For RTOS and interrupt work, the FreeRTOS, Zephyr, and CMSIS-RTOS2 reference guides count
as sources too: cite the section you used, not just the project name. Link the source in
your pull request. If two sources disagree, say which one you followed and why; the skill
states its choice explicitly rather than blending both.

## Maintaining synchronization across the pillars

A rule does not live in one file. When you add or rename a rule, update every pillar it
touches, or the skills will contradict the lints and the evals:

1. **The writing skill** — `skills/embedded-c-best-practices/SKILL.md` gets the imperative
   bullet, the failure mode it prevents, and the rule ID in backticks.
2. **The authority digest** — the matching file in
   `skills/embedded-c-best-practices/references/` must define that rule ID in a heading or
   table row. This is the canonical definition; `scripts/check-skill.py` fails when a
   `SKILL.md`, an `examples/*.md`, or `lints/check_arch.py` cites an ID that no digest
   defines.
3. **The review skill** — `skills/embedded-c-review/SKILL.md` lists the rule in the
   priority tier where a reviewer should flag it, using the same ID.
4. **The machine checks** — `lints/check_arch.py` and `lints/.clang-tidy` enforce the rule
   when it is mechanically checkable. If a rule cannot be checked by a script, say so in
   the pull request instead of writing a check that only matches one style.
5. **The evals** — add a grader under `skills/<skill>/evals/<case>/graders/` whose
   assertion proves the rule holds. Graders are one falsifiable sentence each.

Keep the rule ID identical in all five places, and keep every file 100% vendor-neutral:
no vendor SDK headers, register types, or proprietary project names in skills, lints, or
examples. Use generic placeholders such as `vendor_hal.h`, `VENDOR_ADC1`, or
`project_types.h`.

## Good first contributions

- **A rule the skills get wrong or miss.** Open a "Propose a rule" issue with the source,
  a short example of the C the agent writes today, and what it should write instead.
- **A review false positive.** If `embedded-c-review` flags code that is actually safe,
  open a "Review false positive" issue with the file and the finding. These become new
  eval cases.
- **A new eval case.** A realistic firmware prompt, the input files it needs, and one
  binary assertion per grader file. See
  [Testing the skills](README.md#testing-the-skills) for the directory layout.
- **A new architecture check.** A rule that `lints/check_arch.py` can prove in under a
  second, with a fixture that fails before your change and passes after it.
- **A broken install path.** Agents move their skill directories. If an install step in
  the README stopped working, a fix with a link to the agent's current documentation is
  very welcome.

## Making a change

1. **Branch first.** Never edit, commit, or push directly on `main`. Create a feature or
   fix branch (`feat/<topic>` or `fix/<topic>`) and open a pull request.
2. **Edit the skill.** Each skill is `skills/<name>/SKILL.md`. Keep the body under about
   500 lines; longer material belongs in `references/`. Explain why a rule matters, not
   just what it is: agents follow reasoning better than commands.
3. **Compile your examples.** Every C block in the skills, references, and examples must
   build warning-free under
   `gcc -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wsign-conversion`. Run
   `python3 scripts/check-examples.py`; CI runs it too.
4. **Check the lints.** If you touch `lints/`, run `python3 scripts/check-lints.py` and
   confirm on a scratch project that `python3 lints/check_arch.py .` still passes and
   that the `.clang-tidy` checks you edited actually fire.
5. **Validate the skills, manifests, and evals.** Run:

   ```bash
   python3 scripts/check-skill.py
   python3 -m unittest discover -s tests -v
   ```

   The first command checks frontmatter, relative links, orphaned reference digests, rule
   ID synchronization, plugin manifests, the changelog, and every eval case. The second is
   the validator's own unit suite, which must stay green. CI runs both, plus the lint and
   example gates, from [.github/workflows/check.yml](.github/workflows/check.yml).
6. **Run the evals if you changed behavior.** From inside a skill directory:

   ```bash
   claude plugin eval . --allow-tools Write,Edit,Bash --scaffold
   ```

   These are real model runs and are billed, so a maintainer can run them for you if you
   would rather not. Say in the pull request whether you ran them.
7. **Validate the plugin** with `claude plugin validate .` from the repository root.
8. **Add a line to the `[Unreleased]` section of [CHANGELOG.md](CHANGELOG.md)** and bump
   `version` in [.claude-plugin/plugin.json](.claude-plugin/plugin.json) when you change a
   skill or a lint.

## Style

- **Write for an agent reading mid-task:** direct, imperative, one idea per bullet.
- **Prefer a short, compiling C example to a paragraph of description.** Show the
  failure mode and the fixed form side by side.
- **Name APIs `module_ActionNoun()`.** Private helpers are `static`, configuration types
  are `ModuleConfig_t`, and physical quantities carry unit suffixes (`_mv`, `_ma`,
  `_hz`, `_ms`).
- **Braces on every control block**, no `goto`, no dynamic allocation, no recursion, and
  no `float` in production code.
- **Wrap Markdown at about 95 columns** and start every rule bullet with a bold imperative
  sentence followed by the concrete failure mode it prevents.
- **No agent-specific instructions in the skills.** They are standard Agent Skills and
  must work in Claude Code, Factory Droid, OpenAI Codex, GitHub Copilot, Cursor, Gemini
  CLI, and any other agent that reads the format.

## License

By contributing, you agree your contribution is licensed under the MIT license in
[LICENSE](LICENSE).
