export interface AnalysisResult {
  report: IntelligenceReport
  semantic_status: 'not_requested' | 'consent_required' | 'unavailable' | 'complete' | 'failed' | 'rate_limited'
  semantic_error: string | null
  semantic_analysis: {
    category: 'NATURAL_EVENT' | 'HUMAN_MADE_CHANGE' | 'MIXED_OR_INTERACTING' | 'UNCERTAIN'
    observation_types: string[]
    observation: string
    possible_event: string
    supporting_evidence: string[]
    alternative_explanations: string[]
    unknowns: string[]
    limitations: string[]
  } | null
  analysis_id: string
  location: string | null
  before_acquisition_date: string | null
  after_acquisition_date: string | null
  changed_percent: number
  changed_pixels: number
  total_pixels: number
  summary: string
  changed_regions: number
  regions: Array<{
    region_id: string
    x: number
    y: number
    width: number
    height: number
    area: number
    percent_of_valid_area: number
    size_category: 'small' | 'medium' | 'large'
    indicators: { edge_change_percent: number; texture_change_score: number; color_change_score: number }
  }>
  image_dimensions: {
    before: { width: number; height: number }
    after: { width: number; height: number }
    comparison: { width: number; height: number }
  }
  registration_status: 'registered' | 'fallback_unregistered' | 'not_attempted'
  registration_method: string
  comparison_mode: 'registered' | 'original'
  detection_method: string
  warnings: string[]
  processing_duration_ms: number
  annotated_preview: string
  difference_preview: string
  ai_analysis: string | null
}

export interface IntelligenceReport {
  analysis_timestamp: string
  change_category: 'NATURAL_EVENT' | 'HUMAN_MADE_CHANGE' | 'MIXED_OR_INTERACTING' | 'UNCERTAIN'
  classification_source: 'AI_VISION_MODEL' | 'COMPUTER_VISION_HEURISTIC'
  classification_explanation: string
  confidence: number | null
  confidence_explanation: string
  severity: 'LOW_VISUAL_EXTENT' | 'MODERATE_VISUAL_EXTENT' | 'HIGH_VISUAL_EXTENT'
  severity_explanation: string
  supporting_visual_evidence: Array<{ kind: 'annotated_preview' | 'difference_preview' | 'detected_region'; label: string; reference: string }>
  alternative_explanations: string[]
  limitations: string[]
  recommended_verification_steps: string[]
}
