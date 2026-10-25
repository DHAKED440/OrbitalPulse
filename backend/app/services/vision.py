from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import Settings
from app.schemas.analysis import SemanticAnalysis

logger = logging.getLogger(__name__)


class VisionProviderError(RuntimeError):
    pass


class VisionRateLimitError(VisionProviderError):
    pass


class VisionMalformedResponseError(VisionProviderError):
    pass


@dataclass(frozen=True)
class VisionImage:
    label: str
    data_url: str


class VisionProvider(Protocol):
    async def classify(self, images: list[VisionImage], context: dict[str, object]) -> SemanticAnalysis: ...


CLASSIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "category": {
            "type": "string",
            "enum": ["NATURAL_EVENT", "HUMAN_MADE_CHANGE", "MIXED_OR_INTERACTING", "UNCERTAIN"],
        },
        "observation_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "vegetation_loss",
                    "flood_like_water_expansion",
                    "coastal_change",
                    "excavation_or_land_disturbance",
                    "infrastructure_construction",
                    "possible_infrastructure_damage",
                    "fire_related_landscape_change",
                    "seasonal_vegetation_variation",
                    "other",
                    "uncertain",
                ],
            },
        },
        "observation": {"type": "string"},
        "possible_event": {"type": "string"},
        "supporting_evidence": {"type": "array", "items": {"type": "string"}},
        "alternative_explanations": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "category",
        "observation_types",
        "observation",
        "possible_event",
        "supporting_evidence",
        "alternative_explanations",
        "unknowns",
        "limitations",
    ],
}


SYSTEM_INSTRUCTIONS = """You are a cautious satellite-image change interpreter. Computer vision has already identified candidate changed regions; inspect the before/after images and the labeled crops. Treat the CV regions as pointers, not proof. Separate visible observations from possible causes. Report evidence, plausible alternatives, and unknowns. Choose UNCERTAIN when imagery is ambiguous. Do not infer legality, intent, responsibility, exact dates, or ground truth. Do not output a confidence score. Classify only from the visible evidence and provided acquisition metadata. Return the required structured JSON."""


class OpenAIResponsesVisionProvider:
    """OpenAI Responses API adapter using data-URL image inputs and strict JSON schema."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 25,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def classify(self, images: list[VisionImage], context: dict[str, object]) -> SemanticAnalysis:
        content: list[dict[str, str]] = [
            {
                "type": "input_text",
                "text": "Compare the following before/after images. Each image is labeled. CV context (JSON): "
                + json.dumps(context, ensure_ascii=False),
            }
        ]
        for image in images:
            content.append({"type": "input_text", "text": image.label})
            content.append({"type": "input_image", "image_url": image.data_url, "detail": "auto"})

        body = {
            "model": self._model,
            "store": False,
            "max_output_tokens": 1200,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_INSTRUCTIONS}]},
                {"role": "user", "content": content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "orbitalpulse_semantic_analysis",
                    "strict": True,
                    "schema": CLASSIFICATION_SCHEMA,
                }
            },
        }
        timeout = httpx.Timeout(self._timeout_seconds)
        try:
            async with httpx.AsyncClient(timeout=timeout, transport=self._transport) as client:
                response = await client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=body,
                )
        except httpx.TimeoutException as exc:
            raise VisionProviderError("Vision provider request timed out") from exc
        except httpx.RequestError as exc:
            raise VisionProviderError("Vision provider could not be reached") from exc

        if response.status_code == 429:
            raise VisionRateLimitError("Vision provider rate limit reached")
        if response.is_error:
            logger.warning("Vision provider returned HTTP %d", response.status_code)
            raise VisionProviderError("Vision provider request failed")
        try:
            response_json = response.json()
            output_text = _extract_output_text(response_json)
            parsed = json.loads(output_text)
            return SemanticAnalysis.model_validate(parsed)
        except (ValueError, TypeError, KeyError) as exc:
            raise VisionMalformedResponseError("Vision provider returned a malformed classification") from exc


def _extract_output_text(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("Response must be an object")
    output = response.get("output")
    if not isinstance(output, list):
        raise ValueError("Response output is missing")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text" and isinstance(part.get("text"), str):
                texts.append(part["text"])
    if not texts:
        raise ValueError("Response text is missing")
    return "\n".join(texts)


def get_vision_provider(settings: Settings) -> VisionProvider | None:
    """Return a configured provider. Never log or expose secret values."""
    if settings.vision_provider.lower() == "openai" and settings.vision_api_key and settings.vision_model:
        return OpenAIResponsesVisionProvider(
            api_key=settings.vision_api_key,
            model=settings.vision_model,
            timeout_seconds=settings.vision_request_timeout_seconds,
        )
    return None
