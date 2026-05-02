# agent-context-lint

`agent-context-lint` is a small Python CLI for checking the instruction files that AI coding agents read before they act. It helps teams catch risky or stale guidance in `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Cursor rules, and GitHub Copilot instructions before those files waste context or steer agents into bad changes.

The positioning is intentionally narrow: this is a preflight linter for agent context, not a general Markdown checker or policy engine.

## Quickstart

```bash
cd projects/agent-context-lint
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
agent-context-lint scan .
agent-context-lint scan . --format json
```

You can also run from a checkout without installation:

```bash
PYTHONPATH=src python -m agent_context_lint scan /path/to/repo
```

## What It Scans

- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `.cursor/rules/*.md`
- `.cursor/rules/*.mdc`
- `.github/copilot-instructions.md`

## Rules

- `context-size-warning`: large instruction files that can waste model context.
- `secret-like-text`: token, key, password, or private-key-looking text.
- `destructive-command-guidance`: instructions that appear to tell agents to run destructive commands.
- `stale-referenced-path`: backtick path references that do not exist.
- `duplicate-instruction-line`: repeated instruction lines across multiple agent files.

## Example Output

```text
agent-context-lint scan
root: /repo
files scanned: 2
findings: 2

[warning] stale-referenced-path AGENTS.md:4
  Backtick path reference does not exist. (docs/old-plan.md)
[warning] destructive-command-guidance CLAUDE.md:7
  Line appears to instruct agents to run a destructive command.
```

JSON output is available for CI and dashboards:

```bash
agent-context-lint scan . --format json
```

The command exits with status `1` when findings are present and `0` when no findings are found.

## Scope And Non-goals

This MVP focuses on fast, local, explainable checks. It does not call external AI APIs, interpret every shell command, validate Markdown style, or enforce organization-specific policy. Future versions can add configurable thresholds, ignore comments, SARIF output, and CI examples without turning the tool into a broad agent framework.

## Distribution Positioning

Agent instruction files are becoming part of every serious AI-assisted repository, but most repos treat them as unchecked prose. `agent-context-lint` gives maintainers a lightweight quality gate they can run before merging agent instructions, publishing templates, or onboarding another coding assistant.
