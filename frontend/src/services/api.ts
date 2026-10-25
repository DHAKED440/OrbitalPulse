import type { AnalysisResult } from '../types/analysis'

export async function analyzeImages(before: File, after: File): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('before_image', before)
  body.append('after_image', after)
  const response = await fetch('/api/analyze', { method: 'POST', body })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Analysis failed (${response.status})`)
  }
  return response.json() as Promise<AnalysisResult>
}
