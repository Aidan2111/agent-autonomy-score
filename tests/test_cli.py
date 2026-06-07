import contextlib
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from autonomy_score import cli
from autonomy_score.llm import LlmAnalysis


SAMPLE_DIFF = """diff --git a/App/State/SessionStore.swift b/App/State/SessionStore.swift
--- a/App/State/SessionStore.swift
+++ b/App/State/SessionStore.swift
@@ -1,0 +1,5 @@
+final class SessionStore {
+    private var token: String?
+}
"""


class FakeProvider:
    def analyze(self, diff_text, result):
        return LlmAnalysis(
            agreement="partially_agree",
            risk_summary="State code is risky, but the patch is small.",
            missed_risks=("Token lifecycle needs review.",),
            possible_false_positives=("No persistence migration appears in the diff.",),
            recommended_human_action="Ask for architecture approval before implementation.",
            confidence="medium",
        )


class CliTests(unittest.TestCase):
    def test_json_output_omits_llm_analysis_without_flag(self):
        with _temp_diff(SAMPLE_DIFF) as diff_path:
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli.run(["--diff", str(diff_path), "--format", "json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertNotIn("llm_analysis", payload)

    def test_json_output_includes_llm_analysis_with_flag(self):
        with _temp_diff(SAMPLE_DIFF) as diff_path:
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli.run(
                    ["--diff", str(diff_path), "--llm-analysis", "--format", "json"],
                    llm_provider=FakeProvider(),
                )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["recommended_mode"], "Guided Autonomy")
        self.assertEqual(payload["llm_analysis"]["agreement"], "partially_agree")
        self.assertEqual(payload["llm_analysis"]["confidence"], "medium")

    def test_text_and_markdown_output_include_llm_section_with_flag(self):
        with _temp_diff(SAMPLE_DIFF) as diff_path:
            text_stdout = StringIO()
            markdown_stdout = StringIO()
            with contextlib.redirect_stdout(text_stdout):
                text_exit = cli.run(["--diff", str(diff_path), "--llm-analysis"], llm_provider=FakeProvider())
            with contextlib.redirect_stdout(markdown_stdout):
                markdown_exit = cli.run(
                    ["--diff", str(diff_path), "--llm-analysis", "--format", "markdown"],
                    llm_provider=FakeProvider(),
                )

        self.assertEqual(text_exit, 0)
        self.assertEqual(markdown_exit, 0)
        self.assertIn("LLM Advisory Analysis:", text_stdout.getvalue())
        self.assertIn("### LLM Advisory Analysis", markdown_stdout.getvalue())

    def test_missing_api_key_has_helpful_error(self):
        with _temp_diff(SAMPLE_DIFF) as diff_path:
            stdout = StringIO()
            stderr = StringIO()
            with patch.dict("os.environ", {}, clear=True):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = cli.run(["--diff", str(diff_path), "--llm-analysis"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("OPENAI_API_KEY is required", stderr.getvalue())

    def test_intent_only_json_output_scores_pre_work_request(self):
        stdout = StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = cli.run(
                [
                    "--intent-text",
                    "Migrate Core Data schema and update auth token persistence for production users.",
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["recommended_mode"], "Pair Programming")
        self.assertIn("word_count", payload)
        self.assertNotIn("changed_files", payload)

    def test_combined_gate_json_uses_highest_score(self):
        with _temp_diff(SAMPLE_DIFF) as diff_path:
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli.run(
                    [
                        "--intent-text",
                        "Update profile copy.",
                        "--diff",
                        str(diff_path),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["score"], payload["diff"]["score"])
        self.assertIn("intent", payload)
        self.assertIn("diff", payload)
        self.assertEqual(payload["recommended_mode"], "Guided Autonomy")

    def test_intent_only_llm_flag_has_helpful_error(self):
        stdout = StringIO()
        stderr = StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = cli.run(["--intent-text", "Update profile copy.", "--llm-analysis"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("LLM analysis currently requires diff content", stderr.getvalue())

    def test_large_diff_file_has_helpful_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "large.diff"
            path.write_text("x" * (cli.MAX_DIFF_BYTES + 1), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cli.run(["--diff", str(path)])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Diff input is too large", stderr.getvalue())

    def test_markdown_output_handles_backticks_in_paths(self):
        diff = """diff --git a/App/Views/Bad`Name.swift b/App/Views/Bad`Name.swift
--- a/App/Views/Bad`Name.swift
+++ b/App/Views/Bad`Name.swift
@@ -1,0 +1,2 @@
+Text("Hello")
"""
        with _temp_diff(diff) as diff_path:
            stdout = StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = cli.run(["--diff", str(diff_path), "--format", "markdown"])

        self.assertEqual(exit_code, 0)
        self.assertIn("`` App/Views/Bad`Name.swift ``", stdout.getvalue())


@contextlib.contextmanager
def _temp_diff(contents: str):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sample.diff"
        path.write_text(contents, encoding="utf-8")
        yield path


if __name__ == "__main__":
    unittest.main()
