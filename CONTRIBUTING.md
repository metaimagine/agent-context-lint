# Contributing

Thanks for helping make `agent-context-lint` useful for real AI-assisted repositories.

## Local Setup

From this project directory:

```bash
python3 -m pip install -e .
python -m unittest discover -s tests -v
agent-context-lint scan examples
```

You can also run directly from a checkout without installing:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m agent_context_lint scan examples
```

## Contribution Rules

- Keep the tool narrow: lint agent instruction context, not all Markdown or all repository policy.
- Prefer deterministic checks with clear messages over heuristic rules that are hard to explain.
- Add or update focused tests for any scanner or CLI behavior change.
- Do not add network calls, external AI API calls, telemetry, or secret collection.
- Avoid rules that encourage destructive commands or unsafe agent behavior.
- Keep examples small and safe to run locally.

## Pull Request Checklist

- `python -m unittest discover -s tests -v` passes.
- README, changelog, or examples are updated when user-facing behavior changes.
- New rules include a concise code, severity, message, and at least one test.
