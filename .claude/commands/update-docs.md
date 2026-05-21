Review recent code changes in this project and update ARCHITECTURE.md if needed.

## Steps

1. Read the current `ARCHITECTURE.md` at the project root.
2. Run `git diff HEAD~1 HEAD --name-only` (and `git status`) to identify which files changed.
3. Read the changed source files that are relevant to the architecture documentation (skip test files, config, reports, XLS outputs, and non-code files).
4. For each changed file, compare its current implementation against the corresponding section in ARCHITECTURE.md.
5. Update ONLY the sections of ARCHITECTURE.md that are inaccurate or incomplete due to the changes. Do not rewrite sections that are still correct.
6. If no section requires updating (changes were purely internal refactors with no interface/behavior change, or changes were to non-documented files), output the message: "No documentation updates needed." and stop — do NOT modify ARCHITECTURE.md.

## Scope rules

- **Update**: public function signatures, new/removed tools, new CLI flags, new API endpoints, changed data structures, changed scoring formulas, changed file output structure, changed workflow steps.
- **Skip**: internal variable renames, comment changes, whitespace, test files, Excel/JSON data files, report outputs, `.env`, `.gitignore`.
- **Never** rewrite the entire document — surgical edits only.

## Output

After finishing, print a one-line summary of what was changed in ARCHITECTURE.md, or "No documentation updates needed." if nothing changed.
