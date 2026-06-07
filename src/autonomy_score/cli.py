from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from .diff_parser import parse_unified_diff
from .llm import (
    DEFAULT_LLM_MODEL,
    LlmAnalysis,
    LlmAnalysisError,
    LlmProvider,
    OpenAICompatibleProvider,
)
from .scoring import ScoreResult, load_config, score_change


def main(argv: list[str] | None = None) -> int:
    return run(argv)


def run(argv: list[str] | None = None, llm_provider: LlmProvider | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autonomy-score",
        description="Score a code diff to recommend an AI-agent autonomy level.",
    )
    parser.add_argument("--diff", type=Path, help="Path to a unified diff file.")
    parser.add_argument("--base", help="Git base ref to diff against, such as origin/main.")
    parser.add_argument("--staged", action="store_true", help="Score staged git changes.")
    parser.add_argument("--config", type=Path, help="Optional JSON scoring config.")
    parser.add_argument(
        "--llm-analysis",
        action="store_true",
        help="Add advisory-only OpenAI-compatible LLM analysis to the deterministic score.",
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help=f"Model for --llm-analysis. Defaults to AUTONOMY_SCORE_LLM_MODEL or {DEFAULT_LLM_MODEL}.",
    )
    parser.add_argument(
        "--llm-base-url",
        default=None,
        help="Optional OpenAI-compatible base URL. Defaults to OPENAI_BASE_URL.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--max-score",
        type=int,
        help="Exit non-zero if the score is above this threshold.",
    )
    args = parser.parse_args(argv)

    diff_text = _read_diff(args)
    if not diff_text.strip():
        print("No diff content found. Pass --diff, pipe a diff on stdin, or run inside a git repo.")
        return 2

    changed_files = parse_unified_diff(diff_text)
    result = score_change(changed_files, load_config(args.config))
    llm_analysis = None
    if args.llm_analysis:
        try:
            provider = llm_provider or OpenAICompatibleProvider.from_env(
                model=args.llm_model,
                base_url=args.llm_base_url,
            )
            llm_analysis = provider.analyze(diff_text, result)
        except LlmAnalysisError as exc:
            print(f"LLM analysis failed: {exc}", file=sys.stderr)
            return 2

    print(_format_result(result, args.format, llm_analysis))

    if args.max_score is not None and result.score > args.max_score:
        return 1
    return 0


def _read_diff(args: argparse.Namespace) -> str:
    if args.diff:
        return args.diff.read_text(encoding="utf-8")
    if args.base:
        return _git_diff([args.base, "--"])
    if args.staged:
        return _git_diff(["--cached"])
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return _git_diff([])


def _git_diff(extra_args: list[str]) -> str:
    completed = subprocess.run(
        ["git", "diff", "--unified=3", *extra_args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def _format_result(result: ScoreResult, output_format: str, llm_analysis: LlmAnalysis | None = None) -> str:
    if output_format == "json":
        data = result.to_dict()
        if llm_analysis:
            data["llm_analysis"] = llm_analysis.to_dict()
        return json.dumps(data, indent=2, sort_keys=True)
    if output_format == "markdown":
        return _format_markdown(result, llm_analysis)
    return _format_text(result, llm_analysis)


def _format_text(result: ScoreResult, llm_analysis: LlmAnalysis | None = None) -> str:
    lines = [
        f"Autonomy Score: {result.score}/10 ({result.band})",
        f"Recommended mode: {result.recommended_mode}",
        f"Summary: {result.summary}",
        f"Files changed: {len(result.changed_files)}",
        f"Lines added/removed: +{result.lines_added}/-{result.lines_removed}",
        "",
        "Signals:",
    ]
    if not result.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.signals:
        prefix = f"+{signal.points}" if signal.points else "cap"
        files = f" [{', '.join(signal.files)}]" if signal.files else ""
        lines.append(f"- {prefix} {signal.name}: {signal.reason}{files}")
    if llm_analysis:
        lines.extend(_format_llm_text(llm_analysis))
    return "\n".join(lines)


def _format_markdown(result: ScoreResult, llm_analysis: LlmAnalysis | None = None) -> str:
    lines = [
        "## Autonomy Score",
        "",
        f"**Score:** {result.score}/10 ({result.band})",
        f"**Recommended mode:** {result.recommended_mode}",
        "",
        result.summary,
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Files changed | {len(result.changed_files)} |",
        f"| Lines added | {result.lines_added} |",
        f"| Lines removed | {result.lines_removed} |",
        "",
        "### Signals",
        "",
    ]
    if not result.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.signals:
        prefix = f"+{signal.points}" if signal.points else "cap"
        files = f" Files: `{', '.join(signal.files)}`." if signal.files else ""
        lines.append(f"- **{prefix} {signal.name}:** {signal.reason}{files}")
    if llm_analysis:
        lines.extend(_format_llm_markdown(llm_analysis))
    return "\n".join(lines)


def _format_llm_text(analysis: LlmAnalysis) -> list[str]:
    return [
        "",
        "LLM Advisory Analysis:",
        f"- Agreement: {analysis.agreement}",
        f"- Confidence: {analysis.confidence}",
        f"- Risk summary: {analysis.risk_summary}",
        "- Missed risks:",
        *_format_text_items(analysis.missed_risks),
        "- Possible false positives:",
        *_format_text_items(analysis.possible_false_positives),
        f"- Recommended human action: {analysis.recommended_human_action}",
    ]


def _format_llm_markdown(analysis: LlmAnalysis) -> list[str]:
    return [
        "",
        "### LLM Advisory Analysis",
        "",
        f"- **Agreement:** {analysis.agreement}",
        f"- **Confidence:** {analysis.confidence}",
        f"- **Risk summary:** {analysis.risk_summary}",
        "- **Missed risks:** " + _format_inline_items(analysis.missed_risks),
        "- **Possible false positives:** " + _format_inline_items(analysis.possible_false_positives),
        f"- **Recommended human action:** {analysis.recommended_human_action}",
    ]


def _format_text_items(items: tuple[str, ...]) -> list[str]:
    if not items:
        return ["  - None"]
    return [f"  - {item}" for item in items]


def _format_inline_items(items: tuple[str, ...]) -> str:
    if not items:
        return "None"
    return "; ".join(items)
