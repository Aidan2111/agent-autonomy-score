from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryDocumentationTests(unittest.TestCase):
    def test_referenced_example_files_exist(self):
        documents = [
            ROOT / "README.md",
            ROOT / "docs" / "scoring" / "llm-analysis.md",
            ROOT / "docs" / "scoring" / "model.md",
        ]
        referenced_examples = set()
        for document in documents:
            text = document.read_text(encoding="utf-8")
            referenced_examples.update(re.findall(r"examples/[A-Za-z0-9_./-]+\.(?:diff|txt|md|json)", text))

        self.assertIn("examples/diffs/core-data-migration.diff", referenced_examples)
        self.assertIn("examples/intents/intent-core-data-migration.txt", referenced_examples)
        for relative_path in sorted(referenced_examples):
            self.assertTrue((ROOT / relative_path).is_file(), relative_path)

    def test_operating_docs_cover_architecture_branching_and_releases(self):
        expected_docs = [
            ROOT / "docs" / "README.md",
            ROOT / "docs" / "engineering" / "architecture.md",
            ROOT / "docs" / "operations" / "runbook.md",
            ROOT / "docs" / "operations" / "branching-and-releases.md",
            ROOT / "docs" / "scoring" / "model.md",
            ROOT / "docs" / "product" / "case-study.md",
        ]
        for document in expected_docs:
            self.assertTrue(document.is_file(), str(document.relative_to(ROOT)))

        architecture = (ROOT / "docs" / "engineering" / "architecture.md").read_text(encoding="utf-8")
        operations = (ROOT / "docs" / "operations" / "runbook.md").read_text(encoding="utf-8")
        branching = (ROOT / "docs" / "operations" / "branching-and-releases.md").read_text(encoding="utf-8")

        self.assertIn("src/autonomy_score/", architecture)
        self.assertIn("Well-Architected", operations)
        self.assertIn("GitHub Flow", branching)
        self.assertIn("protected", branching.lower())

    def test_distribution_and_automation_metadata_are_present(self):
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        test_workflow = (
            ROOT / ".github" / "workflows" / "autonomy-score.yml"
        ).read_text(encoding="utf-8")
        security_workflow = (
            ROOT / ".github" / "workflows" / "security.yml"
        ).read_text(encoding="utf-8")
        dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        release_workflow = (
            ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")

        for field in (
            "[project.urls]",
            'Homepage = "https://github.com/Aidan2111/agent-autonomy-score"',
            'Repository = "https://github.com/Aidan2111/agent-autonomy-score"',
            'Issues = "https://github.com/Aidan2111/agent-autonomy-score/issues"',
        ):
            with self.subTest(field=field):
                self.assertIn(field, pyproject)

        self.assertIn("windows-latest", test_workflow)
        self.assertIn('python-version: "3.10"', test_workflow)
        self.assertIn('python-version: "3.12"', test_workflow)
        self.assertIn("python -m build", test_workflow)
        self.assertIn("python -m twine check", test_workflow)
        self.assertIn("pip-audit", security_workflow)
        self.assertIn("gitleaks", security_workflow)
        self.assertIn('package-ecosystem: "github-actions"', dependabot)
        self.assertIn('tags:', release_workflow)
        self.assertIn('gh release create', release_workflow)

        for project_file in (
            "CHANGELOG.md",
            "CODE_OF_CONDUCT.md",
            "CONTRIBUTING.md",
            "GOVERNANCE.md",
            "LICENSE",
            "SECURITY.md",
            "SUPPORT.md",
        ):
            with self.subTest(project_file=project_file):
                self.assertTrue((ROOT / project_file).is_file())


if __name__ == "__main__":
    unittest.main()
