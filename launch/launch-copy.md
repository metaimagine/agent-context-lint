# Launch Copy

## Short Description

Lint AI-agent instruction files before they drift, leak, or mislead coding agents.

## Announcement

`agent-context-lint` is a small Python CLI for checking the files coding agents read before they act: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules, and GitHub Copilot instructions.

It catches common launch blockers for agent-assisted repos: stale referenced paths, secret-looking text, destructive command guidance, oversized context files, and duplicate instruction lines across agent docs.

The goal is intentionally narrow: a fast preflight check for agent context, with explainable local rules and JSON output for CI.

```bash
python3 -m pip install agent-context-lint
agent-context-lint scan .
agent-context-lint scan . --format json
```

Expected repo: https://github.com/metaimagine/agent-context-lint
