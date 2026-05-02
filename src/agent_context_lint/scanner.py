from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

AGENT_FILENAMES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
MAX_BYTES = 24_000
MAX_LINES = 500

SECRET_PATTERNS = [
    re.compile(r"\b[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*['\"]?[^'\"\s]{12,}"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_=-]{16,}"),
    re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----"),
]

DESTRUCTIVE_PATTERNS = [
    re.compile(r"\brm\s+-[^\n`]*[rf][^\n`]*\s+(?:/|\*|\.|~|\$[A-Z_])"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bgit\s+clean\s+-[^\n`]*[xdf][^\n`]*\b"),
    re.compile(r"\b(?:sudo\s+)?chmod\s+-R\s+777\b"),
]

BACKTICK_RE = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True)
class InstructionFile:
    path: Path
    bytes: int
    lines: int

    def to_dict(self, root: Path) -> dict[str, object]:
        return {
            "path": self.path.relative_to(root).as_posix(),
            "bytes": self.bytes,
            "lines": self.lines,
        }


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    path: Path
    line: int
    message: str
    detail: str = ""
    line_text: str = ""

    def to_dict(self, root: Path) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "severity": self.severity,
            "path": self.path.relative_to(root).as_posix(),
            "line": self.line,
            "message": self.message,
        }
        if self.detail:
            payload["detail"] = self.detail
        if self.line_text:
            payload["line_text"] = self.line_text
        return payload


@dataclass(frozen=True)
class ScanResult:
    root: Path
    files: list[InstructionFile]
    findings: list[Finding]

    def to_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "summary": {
                "files_scanned": len(self.files),
                "findings": len(self.findings),
            },
            "files": [file.to_dict(self.root) for file in self.files],
            "findings": [finding.to_dict(self.root) for finding in self.findings],
        }


def scan_path(path: Path | str) -> ScanResult:
    root = Path(path).expanduser().resolve()
    if root.is_file():
        root = root.parent

    discovered = discover_instruction_files(root)
    files: list[InstructionFile] = []
    findings: list[Finding] = []
    duplicate_index: dict[str, list[tuple[Path, int, str]]] = {}

    for file_path in discovered:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        files.append(InstructionFile(path=file_path, bytes=len(text.encode("utf-8")), lines=len(lines)))
        findings.extend(_size_findings(file_path, text, lines))
        findings.extend(_line_findings(root, file_path, lines))
        _index_duplicates(duplicate_index, file_path, lines)

    findings.extend(_duplicate_findings(duplicate_index))
    findings.sort(key=lambda item: (item.path.as_posix(), item.line, item.code, item.detail))
    return ScanResult(root=root, files=files, findings=findings)


def discover_instruction_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for filename in AGENT_FILENAMES:
        candidate = root / filename
        if candidate.is_file():
            candidates.append(candidate)

    cursor_rules = root / ".cursor" / "rules"
    if cursor_rules.is_dir():
        candidates.extend(path for path in cursor_rules.iterdir() if path.is_file() and path.suffix in {".md", ".mdc"})

    copilot = root / ".github" / "copilot-instructions.md"
    if copilot.is_file():
        candidates.append(copilot)

    return sorted(set(candidates), key=lambda item: item.relative_to(root).as_posix())


def _size_findings(path: Path, text: str, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    byte_count = len(text.encode("utf-8"))
    if byte_count > MAX_BYTES or len(lines) > MAX_LINES:
        findings.append(
            Finding(
                code="context-size-warning",
                severity="warning",
                path=path,
                line=1,
                message="Instruction file is large enough to waste agent context or hide conflicting guidance.",
                detail=f"{byte_count} bytes, {len(lines)} lines",
            )
        )
    return findings


def _line_findings(root: Path, path: Path, lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines, start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        code="secret-like-text",
                        severity="error",
                        path=path,
                        line=index,
                        message="Line looks like it may contain a token, key, password, or private key material.",
                        line_text=line.strip(),
                    )
                )
                break

        for pattern in DESTRUCTIVE_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        code="destructive-command-guidance",
                        severity="warning",
                        path=path,
                        line=index,
                        message="Line appears to instruct agents to run a destructive command.",
                        line_text=line.strip(),
                    )
                )
                break

        for reference in _backtick_path_references(line):
            if not _reference_exists(root, path.parent, reference):
                findings.append(
                    Finding(
                        code="stale-referenced-path",
                        severity="warning",
                        path=path,
                        line=index,
                        message="Backtick path reference does not exist.",
                        detail=reference,
                        line_text=line.strip(),
                    )
                )
    return findings


def _backtick_path_references(line: str) -> list[str]:
    references: list[str] = []
    for match in BACKTICK_RE.finditer(line):
        value = match.group(1).strip()
        if _looks_like_path(value):
            references.append(value)
    return references


def _looks_like_path(value: str) -> bool:
    if not value or value.startswith(("http://", "https://")):
        return False
    if any(char in value for char in ("\n", "\r")):
        return False
    if " " in value:
        return False
    return "/" in value or value.startswith(("./", "../", ".github/", ".cursor/")) or Path(value).suffix in {
        ".md",
        ".mdc",
        ".py",
        ".toml",
        ".json",
        ".yaml",
        ".yml",
        ".txt",
    }


def _reference_exists(root: Path, file_parent: Path, reference: str) -> bool:
    candidate = Path(reference).expanduser()
    if candidate.is_absolute():
        return candidate.exists()
    return (root / candidate).exists() or (file_parent / candidate).exists()


def _index_duplicates(index: dict[str, list[tuple[Path, int, str]]], path: Path, lines: list[str]) -> None:
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if _is_duplicate_candidate(line):
            index.setdefault(line.casefold(), []).append((path, line_number, line))


def _is_duplicate_candidate(line: str) -> bool:
    if len(line) < 12:
        return False
    if line.startswith(("#", "-", "*")):
        line = line.lstrip("#-* ")
    return bool(line) and not line.startswith("```")


def _duplicate_findings(index: dict[str, list[tuple[Path, int, str]]]) -> list[Finding]:
    findings: list[Finding] = []
    for entries in index.values():
        paths = {entry[0] for entry in entries}
        if len(paths) < 2:
            continue
        for path, line_number, line in entries:
            findings.append(
                Finding(
                    code="duplicate-instruction-line",
                    severity="info",
                    path=path,
                    line=line_number,
                    message="Same instruction line appears in multiple agent instruction files.",
                    line_text=line,
                )
            )
    return findings
