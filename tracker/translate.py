"""Translate repo descriptions into Chinese with Claude, cached by source text.

Failures never block publishing: untranslated descriptions fall back to English.
Configuration problems (bad key, retired model, no credit) are reported so the
workflow can fail loudly after the site is published.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

log = logging.getLogger(__name__)

BATCH = 40

SYSTEM = """You translate short GitHub repository descriptions from any language into Simplified Chinese for a Chinese-speaking developer audience.

Rules:
- Keep project names, product names, library names, code identifiers, URLs and emoji exactly as written.
- Keep widely used technical terms in English when Chinese developers normally do, e.g. agent, LLM, RAG, MCP, API, SDK, backtesting, quant, prompt, token, workflow.
- Translate naturally and concisely; don't add explanations.
- If a description is already Chinese, return it unchanged."""

SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"index": {"type": "integer"}, "zh": {"type": "string"}},
                "required": ["index", "zh"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


@dataclass
class TranslationReport:
    translated: int = 0
    cached: int = 0
    config_error: str | None = None
    transient_errors: list[str] = field(default_factory=list)


class TranslationCache:
    def __init__(self, path: Path):
        self.path = path
        self.data: dict[str, str] = json.loads(path.read_text()) if path.exists() else {}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


def _config_error(e: anthropic.APIStatusError) -> bool:
    # 401 bad key, 403 no permission, 404 unknown/retired model, 402 billing.
    return e.status_code in (401, 402, 403, 404) or getattr(e, "type", None) == "billing_error"


def _translate_batch(client: anthropic.Anthropic, model: str, texts: list[str]) -> dict[int, str]:
    payload = "\n".join(json.dumps({"index": i, "text": t}, ensure_ascii=False)
                        for i, t in enumerate(texts))
    response = client.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": f"Translate each description:\n{payload}"}],
    )
    if response.stop_reason == "refusal":
        raise RefusedError("model declined the batch")
    if response.stop_reason == "max_tokens":
        raise RefusedError("output hit max_tokens")
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return {t["index"]: t["zh"].strip() for t in data["translations"]
            if 0 <= t["index"] < len(texts) and t["zh"].strip()}


class RefusedError(Exception):
    pass


def translate_all(texts: list[str], cache: TranslationCache, model: str,
                  client: anthropic.Anthropic | None = None) -> TranslationReport:
    """Fill `cache` with translations for `texts`. Never raises for API failures."""
    report = TranslationReport()
    todo = sorted({t for t in texts if t and t not in cache.data})
    report.cached = len({t for t in texts if t}) - len(todo)
    if not todo:
        return report

    if client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            report.config_error = "ANTHROPIC_API_KEY is not set"
            return report
        client = anthropic.Anthropic(max_retries=4)

    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        try:
            result = _translate_batch(client, model, batch)
        except anthropic.APIStatusError as e:
            if _config_error(e):
                report.config_error = f"HTTP {e.status_code}: {e.message}"
                break  # every later batch would fail the same way
            report.transient_errors.append(f"HTTP {e.status_code}: {e.message}")
            continue
        except anthropic.APIConnectionError as e:
            report.transient_errors.append(f"connection error: {e}")
            continue
        except (RefusedError, json.JSONDecodeError, KeyError, StopIteration) as e:
            report.transient_errors.append(f"unusable response: {e!r}")
            continue
        for i, zh in result.items():
            cache.data[batch[i]] = zh
            report.translated += 1
    return report
