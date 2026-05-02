# Changelog

All notable changes to this project will be documented in this file.

## v0.1.0 - 2026-05-03

- Initial MVP release of `agent-context-lint`.
- Added local scanning for `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules, and GitHub Copilot instructions.
- Added checks for oversized context files, secret-like text, destructive command guidance, stale backtick path references, and duplicate instruction lines.
- Added text and JSON CLI output for local checks, CI, and dashboards.
