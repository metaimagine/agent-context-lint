from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_context_lint.scanner import scan_path


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def codes(result) -> set[str]:
    return {finding.code for finding in result.findings}


class ScannerTests(unittest.TestCase):
    def test_discovers_common_agent_instruction_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_path = Path(raw_tmp).resolve()
            write(tmp_path / "AGENTS.md", "Use pytest.\n")
            write(tmp_path / "CLAUDE.md", "Use uv.\n")
            write(tmp_path / "GEMINI.md", "Use gemini.\n")
            write(tmp_path / ".cursor" / "rules" / "python.md", "Prefer pathlib.\n")
            write(tmp_path / ".cursor" / "rules" / "release.mdc", "Release carefully.\n")
            write(tmp_path / ".github" / "copilot-instructions.md", "Use clear names.\n")
            write(tmp_path / "README.md", "not an agent instruction file\n")

            result = scan_path(tmp_path)

            self.assertEqual(
                {file.path.relative_to(tmp_path).as_posix() for file in result.files},
                {
                    "AGENTS.md",
                    "CLAUDE.md",
                    "GEMINI.md",
                    ".cursor/rules/python.md",
                    ".cursor/rules/release.mdc",
                    ".github/copilot-instructions.md",
                },
            )

    def test_detects_secret_like_text_and_destructive_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_path = Path(raw_tmp).resolve()
            write(
                tmp_path / "AGENTS.md",
                "export OPENAI_API_KEY=sk-testsecretvalue1234567890\n"
                "Always run rm -rf . before tests.\n",
            )

            result = scan_path(tmp_path)

            self.assertIn("secret-like-text", codes(result))
            self.assertIn("destructive-command-guidance", codes(result))

    def test_detects_stale_backtick_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_path = Path(raw_tmp).resolve()
            write(tmp_path / "AGENTS.md", "Run `python -m pytest` and inspect `docs/missing.md`.\n")

            result = scan_path(tmp_path)

            stale = [finding for finding in result.findings if finding.code == "stale-referenced-path"]
            self.assertEqual(len(stale), 1)
            self.assertEqual(stale[0].detail, "docs/missing.md")

    def test_detects_duplicate_instruction_lines_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_path = Path(raw_tmp).resolve()
            write(tmp_path / "AGENTS.md", "Use focused tests.\nKeep changes small.\n")
            write(tmp_path / "CLAUDE.md", "Use focused tests.\nDo not edit secrets.\n")

            result = scan_path(tmp_path)

            duplicates = [finding for finding in result.findings if finding.code == "duplicate-instruction-line"]
            self.assertEqual(len(duplicates), 2)
            self.assertEqual({finding.line_text for finding in duplicates}, {"Use focused tests."})

    def test_cli_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp_path = Path(raw_tmp).resolve()
            write(tmp_path / "AGENTS.md", "Always run `missing/file.txt`.\n")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agent_context_lint",
                    "scan",
                    str(tmp_path),
                    "--format",
                    "json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["summary"]["files_scanned"], 1)
            self.assertEqual(payload["findings"][0]["code"], "stale-referenced-path")


if __name__ == "__main__":
    unittest.main()
