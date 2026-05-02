from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from agent_context_lint.scanner import Finding, ScanResult, scan_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-context-lint",
        description="Lint AI-agent instruction files for drift, risky guidance, and leaked-looking text.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="scan a repository or directory")
    scan.add_argument("path", nargs="?", default=".", help="path to scan")
    scan.add_argument("--format", choices=("text", "json"), default="text", help="output format")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        result = scan_path(Path(args.path))
        if args.format == "json":
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            print(format_text(result))
        return 1 if result.findings else 0

    parser.error("unknown command")
    return 2


def format_text(result: ScanResult) -> str:
    root = result.root
    lines = [
        "agent-context-lint scan",
        f"root: {root}",
        f"files scanned: {len(result.files)}",
        f"findings: {len(result.findings)}",
    ]

    if not result.findings:
        lines.append("")
        lines.append("No findings.")
        return "\n".join(lines)

    lines.append("")
    for finding in result.findings:
        lines.extend(_format_finding(finding, root))
    return "\n".join(lines).rstrip()


def _format_finding(finding: Finding, root: Path) -> list[str]:
    rel = finding.path.relative_to(root).as_posix()
    location = f"{rel}:{finding.line}" if finding.line else rel
    detail = f" ({finding.detail})" if finding.detail else ""
    return [
        f"[{finding.severity}] {finding.code} {location}",
        f"  {finding.message}{detail}",
    ]
