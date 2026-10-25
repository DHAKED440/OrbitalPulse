from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, Field


class ImageSize(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ImageDimensions(BaseModel):
    before: ImageSize
    after: ImageSize
    comparison: ImageSize


class RegionIndicators(BaseModel):
    edge_change_percent: float = Field(ge=0, le=100)
    texture_change_score: float = Field(ge=0, le=1)
    color_change_score: float = Field(ge=0, le=100)


class DetectedRegion(BaseModel):
    region_id: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    area: int = Field(gt=0)
    percent_of_valid_area: float = Field(ge=0, le=100)
    size_category: Literal["small", "medium", "large"]
    indicators: RegionIndicators


ObservationType = Literal[
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
]


class SemanticAnalysis(BaseModel):
    model_config = {"extra": "forbid"}

    category: Literal["NATURAL_EVENT", "HUMAN_MADE_CHANGE", "MIXED_OR_INTERACTING", "UNCERTAIN"]
    observation_types: list[ObservationType]
    observation: str = Field(min_length=1, max_length=1000)
    possible_event: str = Field(min_length=1, max_length=1000)
    supporting_evidence: list[str]
    alternative_explanations: list[str]
    unknowns: list[str]
    limitations: list[str]


class VisualEvidence(BaseModel):
    kind: Literal["annotated_preview", "difference_preview", "detected_region"]
    label: str
    reference: str


class IntelligenceReport(BaseModel):
    model_config = {"extra": "forbid"}

    analysis_timestamp: datetime
    change_category: Literal["NATURAL_EVENT", "HUMAN_MADE_CHANGE", "MIXED_OR_INTERACTING", "UNCERTAIN"]
    classification_source: Literal["AI_VISION_MODEL", "COMPUTER_VISION_HEURISTIC"]
    classification_explanation: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_explanation: str
    severity: Literal["LOW_VISUAL_EXTENT", "MODERATE_VISUAL_EXTENT", "HIGH_VISUAL_EXTENT"]
    severity_explanation: str
    supporting_visual_evidence: list[VisualEvidence]
    alternative_explanations: list[str]
    limitations: list[str]
    recommended_verification_steps: list[str]


class AnalysisResponse(BaseModel):
    analysis_id: str
    status: str = "complete"
    location: str | None = None
    before_acquisition_date: date | None = None
    after_acquisition_date: date | None = None
    changed_percent: float = Field(ge=0, le=100)
    changed_pixels: int = Field(ge=0)
    total_pixels: int = Field(gt=0)
    summary: str
    changed_regions: int = Field(ge=0)
    regions: list[DetectedRegion] = Field(default_factory=list)
    image_dimensions: ImageDimensions | None = None
    registration_status: Literal["registered", "fallback_unregistered", "not_attempted"] = "not_attempted"
    registration_method: str = "unknown"
    comparison_mode: Literal["registered", "original"] = "original"
    detection_method: str = "Method details are unavailable for this retained report."
    warnings: list[str] = Field(default_factory=list)
    processing_duration_ms: float = Field(default=0, ge=0)
    annotated_preview: str = ""
    difference_preview: str = ""
    ai_analysis: str | None = None
    semantic_status: Literal["not_requested", "consent_required", "unavailable", "complete", "failed", "rate_limited"] = "not_requested"
    semantic_analysis: SemanticAnalysis | None = None
    semantic_error: str | None = None
    report: IntelligenceReport


class SampleAsset(BaseModel):
    filename: str
    url: str
    size_bytes: int = Field(ge=0)
    media_type: str


class SampleScenario(BaseModel):
    id: str
    title: str
    category: str
    description: str
    expected_change: str
    synthetic: bool = True
    before: SampleAsset
    after: SampleAsset


class SamplesResponse(BaseModel):
    samples: list[SampleScenario]
