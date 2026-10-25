import json

import httpx
import pytest
from PIL import Image

from app.core.config import Settings
from app.schemas.analysis import SemanticAnalysis
from app.services.classifier import classify_analysis
from app.services.vision import (
    OpenAIResponsesVisionProvider,
    VisionImage,
    VisionMalformedResponseError,
    VisionRateLimitError,
)


def semantic_payload():
    return {
        "category": "UNCERTAIN",
        "observation_types": ["vegetation_loss"],
        "observation": "The after image appears less vegetated in one area.",
        "possible_event": "Possible vegetation removal or seasonal change.",
        "supporting_evidence": ["A previously green patch appears brown or bare."],
        "alternative_explanations": ["Seasonality", "Different acquisition conditions"],
        "unknowns": ["The cause and timing are unknown."],
        "limitations": ["Imagery alone does not establish intent or responsibility."],
    }


@pytest.mark.asyncio
async def test_openai_adapter_sends_images_and_validates_structured_response():
    captured = {}

    async def handler(request):
        captured["body"] = json.loads(request.content)
        captured["authorization"] = request.headers["Authorization"]
        return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(semantic_payload())}]}]})

    provider = OpenAIResponsesVisionProvider("test-secret", "test-vision-model", transport=httpx.MockTransport(handler))
    result = await provider.classify([VisionImage("before", "data:image/jpeg;base64,AA==")], {"regions": []})

    assert isinstance(result, SemanticAnalysis)
    assert result.category == "UNCERTAIN"
    assert captured["authorization"] == "Bearer test-secret"
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    user_content = captured["body"]["input"][1]["content"]
    assert any(item.get("image_url") == "data:image/jpeg;base64,AA==" for item in user_content)


@pytest.mark.asyncio
async def test_openai_adapter_rejects_malformed_and_out_of_schema_responses():
    async def malformed(request):
        return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text", "text": "not json"}]}]})

    async def invalid_schema(request):
        payload = semantic_payload()
        payload["category"] = "CERTAIN"
        return httpx.Response(200, json={"output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(payload)}]}]})

    for handler in (malformed, invalid_schema):
        provider = OpenAIResponsesVisionProvider("x", "m", transport=httpx.MockTransport(handler))
        with pytest.raises(VisionMalformedResponseError):
            await provider.classify([], {})


@pytest.mark.asyncio
async def test_openai_adapter_maps_rate_limit():
    async def handler(request):
        return httpx.Response(429, json={"error": {"message": "hidden detail"}})

    provider = OpenAIResponsesVisionProvider("x", "m", transport=httpx.MockTransport(handler))
    with pytest.raises(VisionRateLimitError):
        await provider.classify([], {})


@pytest.mark.asyncio
async def test_classifier_prepares_bounded_full_images_and_region_crops(tmp_path):
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    Image.new("RGB", (32, 24), (10, 30, 50)).save(before)
    Image.new("RGB", (16, 12), (90, 70, 40)).save(after)

    class Provider:
        async def classify(self, images, context):
            assert len(images) == 4
            assert images[0].data_url.startswith("data:image/jpeg;base64,")
            assert "region-1" in images[2].label
            assert context["computer_vision"]["regions"][0]["region_id"] == "region-1"
            return SemanticAnalysis.model_validate(semantic_payload())

    result = await classify_analysis(
        Provider(), before, after,
        {"regions": [{"region_id": "region-small", "x": 1, "y": 1, "width": 2, "height": 2, "area": 4}, {"region_id": "region-1", "x": 4, "y": 5, "width": 8, "height": 7, "area": 56}]},
        settings=Settings(vision_max_region_crops=1),
    )
    assert result.category == "UNCERTAIN"
