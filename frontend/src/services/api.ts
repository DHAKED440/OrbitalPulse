import type { AnalysisResult } from '../types/analysis'

export async function analyzeImages(before: File, after: File, comparisonMode: 'registered' | 'original' = 'registered', aiConsent = false): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('before_image', before)
  body.append('after_image', after)
  body.append('comparison_mode', comparisonMode)
  body.append('ai_consent', String(aiConsent))
  const response = await fetch('/api/analyze', { method: 'POST', body })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Analysis failed (${response.status})`)
  }
  return response.json() as Promise<AnalysisResult>
}
