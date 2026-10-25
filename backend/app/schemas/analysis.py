from datetime import date

from pydantic import BaseModel, Field


class DetectedRegion(BaseModel):
    id: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    area_pixels: int = Field(ge=16)


class AnalysisResponse(BaseModel):
    analysis_id: str
    changed_percent: float = Field(ge=0, le=100)
    changed_pixels: int = Field(ge=0)
    total_pixels: int = Field(gt=0)
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    summary: str
    changed_regions: int = Field(ge=0)
    regions: list[DetectedRegion]
    location: str | None = None
    before_date: date | None = None
    after_date: date | None = None
    annotated_image_url: str
    report_url: str
    ai_analysis: str | None = None


class SampleImage(BaseModel):
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
    before: SampleImage
    after: SampleImage
