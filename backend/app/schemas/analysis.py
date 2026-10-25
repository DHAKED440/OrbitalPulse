from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    analysis_id: str
    changed_percent: float = Field(ge=0, le=100)
    changed_pixels: int = Field(ge=0)
    total_pixels: int = Field(gt=0)
    summary: str
    changed_regions: int = Field(ge=0)
    ai_analysis: str | None = None
