export interface AnalysisResult {
  analysis_id: string
  changed_percent: number
  changed_pixels: number
  total_pixels: number
  summary: string
  changed_regions: number
  ai_analysis: string | null
}
