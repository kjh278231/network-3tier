# CLAUDE.md — Project Instructions

## Documentation Auto-Update

After completing **any code modification task** (editing source files, adding features, fixing bugs, refactoring), invoke the `/update-docs` skill to keep `ARCHITECTURE.md` current.

The skill will determine whether documentation updates are actually needed — if the changes don't affect documented interfaces or behavior, it will output "No documentation updates needed." and stop without modifying the file.

**Skip** this step only when the task involved **no code changes** — e.g., read-only analysis, running commands, git operations, or answering questions.

## Project Layout

- `src/network3tier/` — MILP solver core (OR-Tools)
- `analysis_agent/` — AI analysis agent (LangGraph + LiteLLM)
- `network_optimizer.py` — CLI entry point
- `ARCHITECTURE.md` — Architecture documentation (kept up-to-date by `/update-docs`)

## Key Constraints

- `analysis_agent/.env` is **gitignored** and contains real API keys. Never commit it.
- `analysis_agent/report_*.md` is **gitignored**. Never commit reports.
- Excel output files (`output_case*.xls`) use xlwt BIFF8 format with `header=0` (no preamble rows).
