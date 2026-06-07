import unittest
from unittest.mock import patch

from autonomy_score.diff_parser import parse_unified_diff
from autonomy_score.llm import (
    LlmAnalysis,
    LlmAnalysisError,
    MissingOpenAIDependencyError,
    MissingOpenAIKeyError,
    OpenAICompatibleProvider,
)
from autonomy_score.scoring import score_change


class LlmAnalysisTests(unittest.TestCase):
    def test_analysis_from_dict_validates_expected_shape(self):
        analysis = LlmAnalysis.from_dict(
            {
                "agreement": "agree",
                "risk_summary": "The deterministic signals match the diff.",
                "missed_risks": ["Reviewer should inspect migration ordering."],
                "possible_false_positives": [],
                "recommended_human_action": "Approve the plan before code generation.",
                "confidence": "high",
            }
        )

        self.assertEqual(analysis.agreement, "agree")
        self.assertEqual(analysis.confidence, "high")
        self.assertEqual(analysis.missed_risks, ("Reviewer should inspect migration ordering.",))

    def test_analysis_from_dict_rejects_invalid_enum(self):
        with self.assertRaises(LlmAnalysisError):
            LlmAnalysis.from_dict(
                {
                    "agreement": "maybe",
                    "risk_summary": "x",
                    "missed_risks": [],
                    "possible_false_positives": [],
                    "recommended_human_action": "x",
                    "confidence": "high",
                }
            )

    def test_missing_openai_dependency_error_is_actionable(self):
        diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1,0 +1,1 @@
+print("hello")
"""
        result = score_change(parse_unified_diff(diff))
        provider = OpenAICompatibleProvider(api_key="test-key", model="test-model")

        with patch(
            "autonomy_score.llm._import_openai",
            side_effect=MissingOpenAIDependencyError('Install it with: pip install -e ".[llm]"'),
        ):
            with self.assertRaisesRegex(MissingOpenAIDependencyError, r"\.\[llm\]"):
                provider.analyze(diff, result)

    def test_from_env_respects_explicit_empty_environment(self):
        with self.assertRaisesRegex(MissingOpenAIKeyError, "OPENAI_API_KEY"):
            OpenAICompatibleProvider.from_env(env={})


if __name__ == "__main__":
    unittest.main()
