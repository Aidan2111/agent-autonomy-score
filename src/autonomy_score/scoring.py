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
    "test_path_terms": ["test", "tests", "spec", "specs"],
}

LOOP_RE = re.compile(r"\b(for|while|repeat)\b|\.map\s*\{|\.flatMap\s*\{|\.filter\s*\{")


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
