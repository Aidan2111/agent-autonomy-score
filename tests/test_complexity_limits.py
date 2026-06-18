from pathlib import Path
import unittest

from autonomy_score.diff_parser import parse_unified_diff
from autonomy_score.scoring import score_change


ROOT = Path(__file__).resolve().parents[1]


class ComplexityLimitTests(unittest.TestCase):
    def test_docs_frame_complexity_as_a_heuristic_not_big_o_proof(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        scoring_doc = (ROOT / "docs" / "scoring" / "model.md").read_text(encoding="utf-8")

        self.assertIn("complexity-risk heuristic", readme.lower())
        self.assertIn("does not determine exact Big-O", readme)
        self.assertIn("Known Complexity Limits", scoring_doc)
        for hard_case in ("recursion", "divide-and-conquer", "amortized", "library calls"):
            self.assertIn(hard_case, scoring_doc)

    def test_nested_loop_example_surfaces_nested_loop_signal(self):
        diff = _example("complexity/nested-loop.diff")

        result = score_change(parse_unified_diff(diff))

        self.assertTrue(any(signal.name == "big-o:nested-loop" for signal in result.signals))

    def test_recursive_example_documents_false_negative_boundary(self):
        diff = _example("complexity/recursion-limit.diff")

        result = score_change(parse_unified_diff(diff))

        self.assertFalse(any(signal.name == "big-o:nested-loop" for signal in result.signals))
        self.assertTrue(any(signal.name == "algorithmic-risk" for signal in result.signals))

    def test_library_call_example_documents_hidden_complexity_boundary(self):
        diff = _example("complexity/library-call-limit.diff")

        result = score_change(parse_unified_diff(diff))

        self.assertFalse(any(signal.name == "big-o:nested-loop" for signal in result.signals))
        self.assertTrue(any(signal.name == "algorithmic-risk" for signal in result.signals))


def _example(name: str) -> str:
    return (ROOT / "examples" / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
