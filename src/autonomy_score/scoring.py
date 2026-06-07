from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import re
from pathlib import Path
from typing import Iterable

from .diff_parser import ChangedFile


@dataclass(frozen=True)
class Signal:
    name: str
    points: int
    reason: str
    files: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoreResult:
    score: int
    band: str
    recommended_mode: str
    summary: str
    signals: tuple[Signal, ...]
    changed_files: tuple[str, ...]
    lines_added: int
    lines_removed: int

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "band": self.band,
            "recommended_mode": self.recommended_mode,
            "summary": self.summary,
            "signals": [asdict(signal) for signal in self.signals],
            "changed_files": list(self.changed_files),
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


@dataclass(frozen=True)
class IntentScoreResult:
    score: int
    band: str
    recommended_mode: str
    summary: str
    signals: tuple[Signal, ...]
    word_count: int
    mentioned_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "band": self.band,
            "recommended_mode": self.recommended_mode,
            "summary": self.summary,
            "signals": [asdict(signal) for signal in self.signals],
            "word_count": self.word_count,
            "mentioned_paths": list(self.mentioned_paths),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


@dataclass(frozen=True)
class GateResult:
    score: int
    band: str
    recommended_mode: str
    summary: str
    decision_rule: str
    intent: IntentScoreResult
    diff: ScoreResult

    def to_dict(self) -> dict[str, object]:
        return {
            "score": self.score,
            "band": self.band,
            "recommended_mode": self.recommended_mode,
            "summary": self.summary,
            "decision_rule": self.decision_rule,
            "intent": self.intent.to_dict(),
            "diff": self.diff.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


DEFAULT_CONFIG: dict[str, object] = {
    "presentation_path_terms": [
        "view",
        "views",
        "component",
        "components",
        "style",
        "styles",
        "preview",
        "previews",
        "asset",
        "assets",
    ],
    "presentation_extensions": [".css", ".scss", ".html", ".md"],
    "state_path_terms": [
        "state",
        "store",
        "reducer",
        "model",
        "models",
        "persistence",
        "coredata",
        "migration",
        "migrations",
        "schema",
        "database",
        "db",
        "auth",
        "payment",
        "billing",
        "pipeline",
        "sync",
        "cache",
        "session",
    ],
    "critical_content_terms": [
        "delete",
        "drop table",
        "alter table",
        "migration",
        "coredata",
        "schema",
        "transaction",
        "rollback",
        "token",
        "secret",
        "auth",
        "permission",
        "payment",
        "billing",
        "concurrency",
        "actor",
        "taskgroup",
        "async let",
    ],
    "algorithm_terms": [
        "graph",
        "matrix",
        "tree",
        "dfs",
        "bfs",
        "memo",
        "dynamic programming",
        "sort",
        "binary search",
        "dedupe",
        "batch",
        "stream",
        "retry",
        "backoff",
        "rate limit",
    ],
    "intent_high_risk_terms": [
        "auth",
        "authorization",
        "permission",
        "security",
        "token",
        "secret",
        "encryption",
        "payment",
        "billing",
        "invoice",
        "migration",
        "schema",
        "database",
        "core data",
        "coredata",
        "persistence",
        "delete",
        "destructive",
        "backfill",
        "production data",
        "state machine",
        "concurrency",
        "transaction",
        "rollback",
    ],
    "intent_blast_radius_terms": [
        "architecture",
        "platform",
        "global",
        "shared",
        "core",
        "cross-cutting",
        "cross cutting",
        "entire app",
        "all screens",
        "all users",
        "refactor",
        "rewrite",
        "pipeline",
        "sync",
        "cache",
        "infrastructure",
    ],
    "intent_vague_terms": [
        "fix bug",
        "bug fix",
        "improve",
        "optimize",
        "make better",
        "cleanup",
        "clean up",
        "stabilize",
        "harden",
    ],
    "intent_presentation_terms": [
        "copy",
        "label",
        "text",
        "style",
        "color",
        "spacing",
        "padding",
        "font",
        "view",
        "button",
        "screen",
        "preview",
        "swiftui",
        "css",
    ],
    "test_path_terms": ["test", "tests", "spec", "specs"],
}

LOOP_RE = re.compile(r"\b(for|while|repeat)\b|\.map\s*\{|\.flatMap\s*\{|\.filter\s*\{")
PATH_RE = re.compile(r"\b[\w.-]+(?:/[\w.-]+)+\.[A-Za-z0-9]+\b")


def score_change(
    changed_files: Iterable[ChangedFile],
    config: dict[str, object] | None = None,
) -> ScoreResult:
    files = tuple(changed_files)
    active_config = {**DEFAULT_CONFIG, **(config or {})}

    changed_paths = tuple(file.path for file in files)
    added = sum(file.added_line_count for file in files)
    removed = sum(file.removed_line_count for file in files)
    signals: list[Signal] = []
    non_test_files = tuple(file for file in files if not _is_test_path(file.path, active_config))
    has_tests = any(_is_test_path(file.path, active_config) for file in files)

    if len(files) >= 6:
        signals.append(
            Signal(
                "blast-radius:file-count",
                1 if len(files) < 15 else 2,
                f"Change touches {len(files)} files.",
                changed_paths,
            )
        )

    if added >= 100:
        signals.append(
            Signal(
                "blast-radius:added-lines",
                1 if added < 400 else 2,
                f"Change adds {added} lines.",
                changed_paths,
            )
        )

    state_files = _matching_paths(non_test_files, _as_strings(active_config["state_path_terms"]))
    if state_files:
        signals.append(
            Signal(
                "state-or-persistence",
                2,
                "Change touches state, persistence, auth, pipeline, or data-model code.",
                tuple(state_files),
            )
        )

    critical_files = _files_with_terms(non_test_files, _as_strings(active_config["critical_content_terms"]))
    if critical_files:
        signals.append(
            Signal(
                "critical-content",
                2,
                "Added lines include migration, auth, concurrency, destructive, or transactional terms.",
                tuple(critical_files),
            )
        )

    algorithm_files = _files_with_terms(non_test_files, _as_strings(active_config["algorithm_terms"]))
    if algorithm_files:
        signals.append(
            Signal(
                "algorithmic-risk",
                1,
                "Added lines include algorithmic or data-flow terms that may affect complexity.",
                tuple(algorithm_files),
            )
        )

    nested_loop_files = tuple(file.path for file in non_test_files if _has_nested_loop(file.added_lines))
    if nested_loop_files:
        signals.append(
            Signal(
                "big-o:nested-loop",
                2,
                "Added lines appear to introduce nested iteration.",
                nested_loop_files,
            )
        )

    touched_directories = {
        path.rsplit("/", 1)[0]
        for path in changed_paths
        if "/" in path and not _is_test_path(path, active_config)
    }
    if len(touched_directories) >= 4:
        signals.append(
            Signal(
                "blast-radius:directory-spread",
                1,
                f"Change spans {len(touched_directories)} non-test directories.",
                changed_paths,
            )
        )

    if non_test_files and not has_tests and (state_files or critical_files or algorithm_files):
        signals.append(
            Signal(
                "validation:no-tests-in-diff",
                1,
                "Risky production change does not include tests in the same diff.",
                tuple(file.path for file in non_test_files),
            )
        )

    presentation_only = bool(files) and all(_is_presentation_path(file, active_config) for file in files)
    raw_score = 1 + sum(signal.points for signal in signals)
    if presentation_only and not state_files and not critical_files:
        raw_score = min(raw_score, 3)
        signals.append(
            Signal(
                "presentation-only-cap",
                0,
                "All changed files look like presentation, copy, style, or preview work.",
                changed_paths,
            )
        )

    score = max(1, min(10, raw_score))
    band, mode, summary = _band_for_score(score)

    return ScoreResult(
        score=score,
        band=band,
        recommended_mode=mode,
        summary=summary,
        signals=tuple(signals),
        changed_files=changed_paths,
        lines_added=added,
        lines_removed=removed,
    )


def score_intent(intent_text: str, config: dict[str, object] | None = None) -> IntentScoreResult:
    active_config = {**DEFAULT_CONFIG, **(config or {})}
    normalized = _normalize_text(intent_text)
    words = re.findall(r"\b[\w'-]+\b", intent_text)
    word_count = len(words)
    mentioned_paths = tuple(dict.fromkeys(PATH_RE.findall(intent_text.replace("\\", "/"))))
    signals: list[Signal] = []

    high_risk_matches = _matching_terms(normalized, _as_strings(active_config["intent_high_risk_terms"]))
    if high_risk_matches:
        signals.append(
            Signal(
                "intent:critical-domain",
                3,
                "Request mentions security, data, migration, billing, destructive, or concurrency-sensitive work.",
                high_risk_matches,
            )
        )

    state_matches = _matching_terms(normalized, _as_strings(active_config["state_path_terms"]))
    if state_matches:
        signals.append(
            Signal(
                "intent:state-or-persistence",
                2,
                "Request appears to touch state, persistence, auth, cache, sync, or pipeline behavior.",
                state_matches,
            )
        )

    algorithm_matches = _matching_terms(normalized, _as_strings(active_config["algorithm_terms"]))
    if algorithm_matches:
        signals.append(
            Signal(
                "intent:algorithmic-risk",
                1,
                "Request mentions algorithmic, batching, streaming, retry, or data-flow behavior.",
                algorithm_matches,
            )
        )

    blast_radius_matches = _matching_terms(normalized, _as_strings(active_config["intent_blast_radius_terms"]))
    if blast_radius_matches:
        signals.append(
            Signal(
                "intent:blast-radius",
                2,
                "Request implies broad architectural, shared, global, or cross-cutting impact.",
                blast_radius_matches,
            )
        )

    vague_matches = _matching_terms(normalized, _as_strings(active_config["intent_vague_terms"]))
    if vague_matches and not mentioned_paths:
        signals.append(
            Signal(
                "intent:scope-unclear",
                3,
                "Request uses broad goal language without naming concrete files or components.",
                vague_matches,
            )
        )

    if word_count >= 80:
        signals.append(
            Signal(
                "intent:large-request",
                1 if word_count < 180 else 2,
                f"Request has {word_count} words, which often means multiple behaviors or acceptance criteria.",
            )
        )

    test_terms = ("test", "tests", "spec", "coverage", "validation", "verify", "eval", "evaluation")
    risky = bool(high_risk_matches or state_matches or algorithm_matches or blast_radius_matches)
    if risky and not _matching_terms(normalized, test_terms):
        signals.append(
            Signal(
                "intent:validation-not-mentioned",
                1,
                "Risky request does not mention tests, validation, or evaluation.",
            )
        )

    presentation_matches = _matching_terms(normalized, _as_strings(active_config["intent_presentation_terms"]))
    presentation_only = bool(presentation_matches) and not risky

    raw_score = 1 + sum(signal.points for signal in signals)
    if presentation_only:
        raw_score = min(raw_score, 3)
        signals.append(
            Signal(
                "intent:presentation-only-cap",
                0,
                "Request appears limited to presentation, copy, style, or UI surface polish.",
                presentation_matches,
            )
        )

    score = max(1, min(10, raw_score))
    band, mode, summary = _band_for_score(score)

    return IntentScoreResult(
        score=score,
        band=band,
        recommended_mode=mode,
        summary=summary,
        signals=tuple(signals),
        word_count=word_count,
        mentioned_paths=mentioned_paths,
    )


def combine_intent_and_diff(intent: IntentScoreResult, diff: ScoreResult) -> GateResult:
    score = max(intent.score, diff.score)
    band, mode, _ = _band_for_score(score)
    decision_rule = "highest risk wins across pre-work intent and post-work diff"
    if intent.score > diff.score:
        summary = (
            "Pre-work intent is riskier than the resulting diff; keep the agent constrained by the original "
            "task risk before authorizing implementation or merge."
        )
    elif diff.score > intent.score:
        summary = (
            "Post-work diff is riskier than the original intent; treat this as possible scope drift and require "
            "review at the higher diff risk level."
        )
    else:
        summary = "Intent and diff agree on the autonomy band; use that shared risk level for the workflow gate."

    return GateResult(
        score=score,
        band=band,
        recommended_mode=mode,
        summary=summary,
        decision_rule=decision_rule,
        intent=intent,
        diff=diff,
    )


def load_config(path: str | Path | None) -> dict[str, object] | None:
    if not path:
        return None
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _as_strings(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).lower() for item in value)
    return ()


def _matching_paths(files: Iterable[ChangedFile], terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for file in files:
        normalized = file.path.lower().replace("\\", "/")
        parts = normalized.replace(".", "/").split("/")
        if any(term in parts or term in normalized for term in terms):
            matches.append(file.path)
    return matches


def _files_with_terms(files: Iterable[ChangedFile], terms: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for file in files:
        text = "\n".join(file.added_lines).lower()
        if any(term in text for term in terms):
            matches.append(file.path)
    return matches


def _matching_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    matches: list[str] = []
    for term in terms:
        if not term:
            continue
        escaped = re.escape(term).replace(r"\ ", r"[\s-]+")
        if re.search(rf"(?<![\w-]){escaped}(?![\w-])", text):
            matches.append(term)
    return tuple(matches)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _has_nested_loop(lines: tuple[str, ...]) -> bool:
    loop_indents: list[int] = []
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        loop_indents = [existing for existing in loop_indents if existing < indent + 8]
        if LOOP_RE.search(line):
            if any(indent > existing for existing in loop_indents):
                return True
            loop_indents.append(indent)
    return False


def _is_test_path(path: str, config: dict[str, object]) -> bool:
    normalized = path.lower().replace("\\", "/")
    terms = _as_strings(config["test_path_terms"])
    return any(f"/{term}/" in f"/{normalized}/" or normalized.endswith(f"_{term}.py") for term in terms)


def _is_presentation_path(file: ChangedFile, config: dict[str, object]) -> bool:
    normalized = file.path.lower().replace("\\", "/")
    presentation_terms = _as_strings(config["presentation_path_terms"])
    presentation_extensions = _as_strings(config["presentation_extensions"])
    if file.extension in presentation_extensions:
        return True
    return any(term in normalized for term in presentation_terms)


def _band_for_score(score: int) -> tuple[str, str, str]:
    if score <= 3:
        return (
            "Low Risk",
            "Unsupervised",
            "Agent can implement feedback, write code, and open a PR with normal review.",
        )
    if score <= 7:
        return (
            "Medium Risk",
            "Guided Autonomy",
            "Agent should propose the approach first; a human approves architecture before code generation.",
        )
    return (
        "High Risk",
        "Pair Programming",
        "Blast radius is large enough that the agent should work as a copilot under active human supervision.",
    )
