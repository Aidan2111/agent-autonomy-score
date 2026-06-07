from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
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
from .scoring import (
    GateResult,
    IntentScoreResult,
    ScoreResult,
    combine_intent_and_diff,
    load_config,
    score_change,
    score_intent,
)

MAX_DIFF_BYTES = 2_000_000
MAX_INTENT_BYTES = 100_000


class InputTooLargeError(ValueError):
    pass


def main(argv: list[str] | None = None) -> int:
    return run(argv)


def run(argv: list[str] | None = None, llm_provider: LlmProvider | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autonomy-score",
        description="Score an implementation intent, code diff, or both to recommend an AI-agent autonomy level.",
    )
    parser.add_argument("--intent", type=Path, help="Path to a feature request, bug report, or task brief.")
    parser.add_argument("--intent-text", help="Inline feature request, bug report, or task brief.")
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

    try:
        intent_text = _read_intent(args)
        diff_text = _read_diff(args, has_intent_input=bool(intent_text))
    except InputTooLargeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not diff_text.strip() and not intent_text.strip():
        print(
            "No intent or diff content found. Pass --intent, --intent-text, --diff, pipe a diff on stdin, "
            "or run inside a git repo."
        )
        return 2

    config = load_config(args.config)
    intent_result = score_intent(intent_text, config) if intent_text.strip() else None
    diff_result = None
    if diff_text.strip():
        diff_result = score_change(parse_unified_diff(diff_text), config)

    llm_analysis = None
    if args.llm_analysis:
        if diff_result is None:
            print("LLM analysis currently requires diff content; pass --diff, --base, --staged, or pipe a diff.", file=sys.stderr)
            return 2
        try:
            provider = llm_provider or OpenAICompatibleProvider.from_env(
                model=args.llm_model,
                base_url=args.llm_base_url,
            )
            llm_analysis = provider.analyze(diff_text, diff_result)
        except LlmAnalysisError as exc:
            print(f"LLM analysis failed: {exc}", file=sys.stderr)
            return 2

    if intent_result and diff_result:
        result: ScoreResult | IntentScoreResult | GateResult = combine_intent_and_diff(intent_result, diff_result)
        output = _format_gate_result(result, args.format, llm_analysis)
    elif intent_result:
        result = intent_result
        output = _format_intent_result(intent_result, args.format)
    elif diff_result:
        result = diff_result
        output = _format_result(diff_result, args.format, llm_analysis)
    else:
        print("No scorable content found.")
        return 2

    print(output)

    if args.max_score is not None and result.score > args.max_score:
        return 1
    return 0


def _read_intent(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.intent:
        parts.append(_read_limited_file(args.intent, MAX_INTENT_BYTES, "intent"))
    if args.intent_text:
        _ensure_within_limit(args.intent_text, MAX_INTENT_BYTES, "intent")
        parts.append(args.intent_text)
    return "\n\n".join(parts)


def _read_diff(args: argparse.Namespace, has_intent_input: bool = False) -> str:
    if args.diff:
        return _read_limited_file(args.diff, MAX_DIFF_BYTES, "diff")
    if args.base:
        return _git_diff([args.base, "--"])
    if args.staged:
        return _git_diff(["--cached"])
    if not sys.stdin.isatty():
        diff_text = sys.stdin.read(MAX_DIFF_BYTES + 1)
        _ensure_within_limit(diff_text, MAX_DIFF_BYTES, "diff")
        return diff_text
    if has_intent_input:
        return ""
    return _git_diff([])


def _git_diff(extra_args: list[str]) -> str:
    process = subprocess.Popen(
        ["git", "diff", "--unified=3", *extra_args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if process.stdout is None:
        return ""
    output = process.stdout.read(MAX_DIFF_BYTES + 1)
    if len(output) > MAX_DIFF_BYTES:
        process.kill()
        process.wait()
        raise InputTooLargeError(
            f"Diff input is too large. Limit is {MAX_DIFF_BYTES} bytes; use a smaller diff or tune the workflow."
        )
    return_code = process.wait()
    if return_code != 0:
        return ""
    return output.decode("utf-8", errors="replace")


def _read_limited_file(path: Path, max_bytes: int, label: str) -> str:
    size = path.stat().st_size
    if size > max_bytes:
        raise InputTooLargeError(
            f"{label.title()} input is too large. Limit is {max_bytes} bytes, got {size} bytes: {path}"
        )
    return path.read_text(encoding="utf-8")


def _ensure_within_limit(text: str, max_bytes: int, label: str) -> None:
    size = len(text.encode("utf-8"))
    if size > max_bytes:
        raise InputTooLargeError(f"{label.title()} input is too large. Limit is {max_bytes} bytes, got {size} bytes.")


def _format_result(result: ScoreResult, output_format: str, llm_analysis: LlmAnalysis | None = None) -> str:
    if output_format == "json":
        data = result.to_dict()
        if llm_analysis:
            data["llm_analysis"] = llm_analysis.to_dict()
        return json.dumps(data, indent=2, sort_keys=True)
    if output_format == "markdown":
        return _format_markdown(result, llm_analysis)
    return _format_text(result, llm_analysis)


def _format_intent_result(result: IntentScoreResult, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(result.to_dict(), indent=2, sort_keys=True)
    if output_format == "markdown":
        return _format_intent_markdown(result)
    return _format_intent_text(result)


def _format_gate_result(result: GateResult, output_format: str, llm_analysis: LlmAnalysis | None = None) -> str:
    if output_format == "json":
        data = result.to_dict()
        if llm_analysis:
            data["llm_analysis"] = llm_analysis.to_dict()
        return json.dumps(data, indent=2, sort_keys=True)
    if output_format == "markdown":
        return _format_gate_markdown(result, llm_analysis)
    return _format_gate_text(result, llm_analysis)


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
        lines.append(_format_signal_text(signal, "files"))
    if llm_analysis:
        lines.extend(_format_llm_text(llm_analysis))
    return "\n".join(lines)


def _format_intent_text(result: IntentScoreResult) -> str:
    lines = [
        f"Intent Autonomy Score: {result.score}/10 ({result.band})",
        f"Recommended mode: {result.recommended_mode}",
        f"Summary: {result.summary}",
        f"Words: {result.word_count}",
    ]
    if result.mentioned_paths:
        lines.append(f"Mentioned paths: {', '.join(result.mentioned_paths)}")
    lines.extend(["", "Signals:"])
    if not result.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.signals:
        lines.append(_format_signal_text(signal, "terms"))
    return "\n".join(lines)


def _format_gate_text(result: GateResult, llm_analysis: LlmAnalysis | None = None) -> str:
    lines = [
        f"Autonomy Gate Score: {result.score}/10 ({result.band})",
        f"Recommended mode: {result.recommended_mode}",
        f"Decision rule: {result.decision_rule}",
        f"Summary: {result.summary}",
        "",
        f"Intent score: {result.intent.score}/10 ({result.intent.band})",
        f"Diff score: {result.diff.score}/10 ({result.diff.band})",
        "",
        "Intent signals:",
    ]
    if not result.intent.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.intent.signals:
        lines.append(_format_signal_text(signal, "terms"))
    lines.extend(["", "Diff signals:"])
    if not result.diff.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.diff.signals:
        lines.append(_format_signal_text(signal, "files"))
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
        lines.append(_format_signal_markdown(signal, "files"))
    if llm_analysis:
        lines.extend(_format_llm_markdown(llm_analysis))
    return "\n".join(lines)


def _format_intent_markdown(result: IntentScoreResult) -> str:
    lines = [
        "## Intent Autonomy Score",
        "",
        f"**Score:** {result.score}/10 ({result.band})",
        f"**Recommended mode:** {result.recommended_mode}",
        "",
        result.summary,
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Words | {result.word_count} |",
        f"| Mentioned paths | {_format_inline_items(result.mentioned_paths)} |",
        "",
        "### Signals",
        "",
    ]
    if not result.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.signals:
        lines.append(_format_signal_markdown(signal, "terms"))
    return "\n".join(lines)


def _format_gate_markdown(result: GateResult, llm_analysis: LlmAnalysis | None = None) -> str:
    lines = [
        "## Autonomy Gate Score",
        "",
        f"**Score:** {result.score}/10 ({result.band})",
        f"**Recommended mode:** {result.recommended_mode}",
        f"**Decision rule:** {result.decision_rule}",
        "",
        result.summary,
        "",
        "| Pass | Score | Band |",
        "| --- | ---: | --- |",
        f"| Intent | {result.intent.score}/10 | {result.intent.band} |",
        f"| Diff | {result.diff.score}/10 | {result.diff.band} |",
        "",
        "### Intent Signals",
        "",
    ]
    if not result.intent.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.intent.signals:
        lines.append(_format_signal_markdown(signal, "terms"))
    lines.extend(["", "### Diff Signals", ""])
    if not result.diff.signals:
        lines.append("- No risk signals detected beyond the base score.")
    for signal in result.diff.signals:
        lines.append(_format_signal_markdown(signal, "files"))
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


def _format_signal_text(signal, detail_label: str) -> str:
    prefix = f"+{signal.points}" if signal.points else "cap"
    details = f" [{detail_label}: {', '.join(signal.files)}]" if signal.files else ""
    return f"- {prefix} {signal.name}: {signal.reason}{details}"


def _format_signal_markdown(signal, detail_label: str) -> str:
    prefix = f"+{signal.points}" if signal.points else "cap"
    details = f" {detail_label.title()}: {_format_code_items(signal.files)}." if signal.files else ""
    return f"- **{prefix} {_escape_markdown_text(signal.name)}:** {_escape_markdown_text(signal.reason)}{details}"


def _format_inline_items(items: tuple[str, ...]) -> str:
    if not items:
        return "None"
    return "; ".join(_escape_markdown_table_cell(item) for item in items)


def _format_code_items(items: tuple[str, ...]) -> str:
    return ", ".join(_format_code_item(item) for item in items)


def _format_code_item(value: str) -> str:
    longest_tick_run = max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)
    delimiter = "`" * (longest_tick_run + 1)
    padding = " " if longest_tick_run else ""
    return f"{delimiter}{padding}{value}{padding}{delimiter}"


def _escape_markdown_table_cell(value: str) -> str:
    return _escape_markdown_text(value).replace("|", "\\|")


def _escape_markdown_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
