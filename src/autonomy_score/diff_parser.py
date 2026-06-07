from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath


@dataclass(frozen=True)
class ChangedFile:
    path: str
    added_lines: tuple[str, ...] = field(default_factory=tuple)
    removed_lines: tuple[str, ...] = field(default_factory=tuple)

    @property
    def extension(self) -> str:
        return PurePosixPath(self.path).suffix.lower()

    @property
    def added_line_count(self) -> int:
        return len(self.added_lines)

    @property
    def removed_line_count(self) -> int:
        return len(self.removed_lines)


def parse_unified_diff(diff_text: str) -> list[ChangedFile]:
    """Parse a unified diff into files and changed lines.

    The parser intentionally ignores hunk context and only keeps added/removed
    lines. That keeps the scoring model transparent and language-agnostic.
    """
    files: list[dict[str, object]] = []
    current: dict[str, object] | None = None

    def ensure_file(path: str) -> dict[str, object]:
        nonlocal current
        if current is None or current["path"] != path:
            current = {"path": path, "added": [], "removed": []}
            files.append(current)
        return current

    for raw_line in diff_text.splitlines():
        line = raw_line.rstrip("\n")

        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                path = _strip_git_prefix(parts[3])
                current = {"path": path, "added": [], "removed": []}
                files.append(current)
            continue

        if line.startswith("+++ "):
            path = line[4:].strip()
            if path != "/dev/null":
                path = _strip_git_prefix(path)
                if current is None:
                    current = ensure_file(path)
                else:
                    current["path"] = path
            continue

        if current is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current["added"].append(line[1:])  # type: ignore[index]
        elif line.startswith("-") and not line.startswith("---"):
            current["removed"].append(line[1:])  # type: ignore[index]

    if not files and diff_text.strip():
        return [ChangedFile(path="stdin", added_lines=tuple(diff_text.splitlines()))]

    return [
        ChangedFile(
            path=str(item["path"]),
            added_lines=tuple(item["added"]),  # type: ignore[arg-type]
            removed_lines=tuple(item["removed"]),  # type: ignore[arg-type]
        )
        for item in files
    ]


def _strip_git_prefix(path: str) -> str:
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path

