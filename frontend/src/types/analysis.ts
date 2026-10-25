export interface DetectedRegion {
  id: string
  x: number
  y: number
  width: number
  height: number
  area_pixels: number
}

export interface AnalysisResult {
  analysis_id: string
  changed_percent: number
  changed_pixels: number
  total_pixels: number
  image_width: number
  image_height: number
  summary: string
  changed_regions: number
  regions: DetectedRegion[]
  location: string | null
  before_date: string | null
  after_date: string | null
  annotated_image_url: string
  report_url: string
  ai_analysis: string | null
}

export interface ApiHealth {
  status: 'ok'
  vision_provider: string
}

export interface SampleImage {
  filename: string
  url: string
  size_bytes: number
  media_type: string
}

export interface SampleScenario {
  id: string
  title: string
  category: string
  description: string
  expected_change: string
  synthetic: boolean
  before: SampleImage
  after: SampleImage
}

export interface AnalyzeMetadata {
  location?: string
  before_date?: string
  after_date?: string
}
