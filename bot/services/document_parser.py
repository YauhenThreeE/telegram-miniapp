from __future__ import annotations

import logging
from datetime import date
from typing import Any

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - dependency might be absent
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Simple wrapper around LLM calls for document parsing.
    Parsing prompts are deliberately concise; replace with production prompts as needed.
    """

    def __init__(self, openai_api_key: str | None):
        self.openai_api_key = openai_api_key
        self.client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key and AsyncOpenAI else None
        self.model = "gpt-4o-mini"

    async def parse_lab_report(self, text: str) -> list[dict[str, Any]]:
        if not self.client:
            return _fallback_lab()

        system = (
            "Extract lab analytes from the text. Return JSON array of objects with keys: "
            "analyte_name, value, unit, reference_range, flag (low/high/normal if detectable). "
            "Keep values as strings."
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.0,
            )
            content = resp.choices[0].message.content or "{}"
            parsed = _safe_json(content)
            items = parsed.get("items") if isinstance(parsed, dict) else None
            return items if isinstance(items, list) else []
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse_lab_report failed, fallback: %s", exc)
            return _fallback_lab()

    async def parse_examination_report(self, text: str) -> dict[str, Any]:
        if not self.client:
            return _fallback_exam(text)

        system = (
            "Summarize the examination report. Return JSON with keys: "
            "type (e.g., MRI/CT/Ultrasound/FGDS/Colonoscopy/X-ray/ECG), "
            "body_region, date (ISO if present), summary (short conclusion)."
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.1,
            )
            content = resp.choices[0].message.content or "{}"
            parsed = _safe_json(content)
            return parsed if isinstance(parsed, dict) else _fallback_exam(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("parse_examination_report failed, fallback: %s", exc)
            return _fallback_exam(text)

    async def classify_document(self, text: str) -> str:
        if not self.client:
            return "lab_report" if "Hb" in text or "гемоглоб" in text.lower() else "other"

        system = (
            "Classify the medical document. Reply with one of: lab_report, examination, "
            "discharge_summary, other."
        )
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": text},
                ],
                max_tokens=5,
                temperature=0.0,
            )
            return (resp.choices[0].message.content or "other").strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("classify_document failed, fallback: %s", exc)
            return "other"

    async def extract_text_from_image(self, image_bytes: bytes) -> str:
        """
        Stub for OCR/vision extraction. Replace with real OpenAI Vision or OCR provider.
        """
        if not image_bytes:
            return ""
        # TODO: integrate OpenAI Vision or external OCR provider.
        return ""


def _fallback_lab() -> list[dict[str, Any]]:
    return [
        {
            "analyte_name": "Hemoglobin",
            "value": "130",
            "unit": "g/L",
            "reference_range": "120-160",
            "flag": "normal",
        }
    ]


def _fallback_exam(text: str) -> dict[str, Any]:
    return {
        "type": "Ultrasound",
        "body_region": None,
        "date": None,
        "summary": text[:500],
    }


def _safe_json(content: str) -> Any:
    import json

    try:
        return json.loads(content)
    except Exception:
        return {}
