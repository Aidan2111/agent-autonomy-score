from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from typing import Mapping, Protocol

from .scoring import ScoreResult


DEFAULT_LLM_MODEL = "gpt-4.1-mini"
MAX_DIFF_CHARS = 60000


class LlmAnalysisError(RuntimeError):
    """Base error for optional LLM analysis failures."""


class MissingOpenAIKeyError(LlmAnalysisError):
    """Raised when --llm-analysis is used without an API key."""


class MissingOpenAIDependencyError(LlmAnalysisError):
    """Raised when the optional OpenAI SDK dependency is unavailable."""


@dataclass(frozen=True)
class LlmAnalysis:
    agreement: str
    risk_summary: str
    missed_risks: tuple[str, ...]
    possible_false_positives: tuple[str, ...]
    recommended_human_action: str
    confidence: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["missed_risks"] = list(self.missed_risks)
        data["possible_false_positives"] = list(self.possible_false_positives)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "LlmAnalysis":
        agreement = _require_enum(data, "agreement", ("agree", "partially_agree", "disagree"))
        confidence = _require_enum(data, "confidence", ("low", "medium", "high"))
        return cls(
            agreement=agreement,
            risk_summary=_require_string(data, "risk_summary"),
            missed_risks=_require_string_tuple(data, "missed_risks"),
            possible_false_positives=_require_string_tuple(data, "possible_false_positives"),
            recommended_human_action=_require_string(data, "recommended_human_action"),
            confidence=confidence,
        )


class LlmProvider(Protocol):
    def analyze(self, diff_text: str, result: ScoreResult) -> LlmAnalysis:
        """Return an advisory-only analysis for a deterministic score."""


LLM_ANALYSIS_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "agreement": {
            "type": "string",
            "enum": ["agree", "partially_agree", "disagree"],
            "description": "Whether the LLM agrees with the deterministic score and mode.",
        },
        "risk_summary": {
            "type": "string",
            "description": "Short explanation of the highest-impact risk factors in the diff.",
        },
        "missed_risks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Risks the deterministic scorer may have missed.",
        },
        "possible_false_positives": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Signals that may overstate the actual risk.",
        },
        "recommended_human_action": {
            "type": "string",
            "description": "What a reviewer should do before letting the agent continue.",
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Confidence in this advisory analysis.",
        },
    },
    "required": [
        "agreement",
        "risk_summary",
        "missed_risks",
        "possible_false_positives",
        "recommended_human_action",
        "confidence",
    ],
}


SYSTEM_PROMPT = """You are an advisory code-risk reviewer for an agentic SDLC gate.

You will receive:
- a deterministic autonomy score
- the deterministic risk signals
- a unified diff

Your job is to provide a second-opinion analysis. You are advisory only.
Do not change the deterministic score, band, or recommended mode. Focus on
agreement, missed risks, possible false positives, and the human action that
would make the next agent step safer.
"""


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_LLM_MODEL,
        base_url: str | None = None,
    ) -> None:
        if not api_key:
            raise MissingOpenAIKeyError(
                "OPENAI_API_KEY is required for --llm-analysis. "
                "Set it in your environment or run without --llm-analysis."
            )
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @classmethod
    def from_env(
        cls,
        *,
        model: str | None = None,
        base_url: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> "OpenAICompatibleProvider":
        active_env = env if env is not None else os.environ
        selected_model = model or active_env.get("AUTONOMY_SCORE_LLM_MODEL") or DEFAULT_LLM_MODEL
        selected_base_url = base_url or active_env.get("OPENAI_BASE_URL")
        return cls(
            api_key=active_env.get("OPENAI_API_KEY", ""),
            model=selected_model,
            base_url=selected_base_url,
        )

    def analyze(self, diff_text: str, result: ScoreResult) -> LlmAnalysis:
        OpenAI = _import_openai()
        kwargs = {"api_key": self.api_key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        client = OpenAI(**kwargs)
        payload = _build_user_payload(diff_text, result)
        try:
            response = client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": payload},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "autonomy_llm_analysis",
                        "schema": LLM_ANALYSIS_SCHEMA,
                        "strict": True,
                    }
                },
            )
        except AttributeError as exc:
            raise LlmAnalysisError(
                'The installed OpenAI SDK does not expose the Responses API. '
                'Upgrade with: pip install -U "openai>=1.68.0"'
            ) from exc
        except Exception as exc:
            raise LlmAnalysisError(f"OpenAI-compatible request failed: {exc}") from exc
        raw_text = _extract_response_text(response)
        try:
            decoded = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise LlmAnalysisError("LLM response was not valid JSON.") from exc
        return LlmAnalysis.from_dict(decoded)


def _import_openai():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise MissingOpenAIDependencyError(
            'OpenAI SDK is required for --llm-analysis. Install it with: pip install -e ".[llm]"'
        ) from exc
    return OpenAI


def _build_user_payload(diff_text: str, result: ScoreResult) -> str:
    truncated = len(diff_text) > MAX_DIFF_CHARS
    visible_diff = diff_text[:MAX_DIFF_CHARS]
    payload = {
        "deterministic_result": result.to_dict(),
        "diff_truncated": truncated,
        "diff_characters_included": len(visible_diff),
        "unified_diff": visible_diff,
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _extract_response_text(response: object) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    raise LlmAnalysisError("LLM response did not include output_text.")


def _require_string(data: Mapping[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LlmAnalysisError(f"LLM response field {key!r} must be a non-empty string.")
    return value


def _require_enum(data: Mapping[str, object], key: str, allowed: tuple[str, ...]) -> str:
    value = _require_string(data, key)
    if value not in allowed:
        raise LlmAnalysisError(f"LLM response field {key!r} must be one of: {', '.join(allowed)}.")
    return value


def _require_string_tuple(data: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LlmAnalysisError(f"LLM response field {key!r} must be a list of strings.")
    return tuple(item for item in value if item.strip())
