import type { AnalysisResult, SampleAsset, SampleScenario } from '../types/analysis'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')
const REQUEST_TIMEOUT_MS = 60_000

function timedFetch(url: string, init: RequestInit = {}): Promise<Response> {
  return fetch(url, { ...init, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) })
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

export async function listSamples(): Promise<SampleScenario[]> {
  const response = await timedFetch(apiUrl('/api/samples'))
  if (!response.ok) throw new Error(`Sample listing failed (${response.status})`)
  const payload: unknown = await response.json()
  if (!payload || typeof payload !== 'object' || !('samples' in payload) || !Array.isArray(payload.samples)) throw new Error('The API returned an invalid sample listing.')
  const samples = payload.samples
  if (!samples.every((item): item is SampleScenario => {
    if (!item || typeof item !== 'object') return false
    const sample = item as Partial<SampleScenario>
    const validAsset = (asset: unknown): asset is SampleAsset => Boolean(asset && typeof asset === 'object' && typeof (asset as SampleAsset).filename === 'string' && typeof (asset as SampleAsset).url === 'string' && typeof (asset as SampleAsset).media_type === 'string' && typeof (asset as SampleAsset).size_bytes === 'number')
    return typeof sample.id === 'string' && typeof sample.title === 'string' && typeof sample.category === 'string' && typeof sample.description === 'string' && typeof sample.expected_change === 'string' && sample.synthetic === true && validAsset(sample.before) && validAsset(sample.after)
  })) throw new Error('The API returned an invalid sample scenario.')
  return samples
}

export async function getSampleFile(asset: SampleAsset): Promise<File> {
  const response = await timedFetch(apiUrl(asset.url))
  if (!response.ok) throw new Error(`Sample image download failed (${response.status})`)
  const blob = await response.blob()
  if (!blob.type.startsWith('image/')) throw new Error('The sample endpoint did not return an image.')
  return new File([blob], asset.filename, { type: asset.media_type })
}

export async function analyzeImages(
  before: File,
  after: File,
  comparisonMode: 'registered' | 'original' = 'registered',
  aiConsent = false,
  metadata: { location?: string; beforeDate?: string; afterDate?: string } = {},
): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('before_image', before)
  body.append('after_image', after)
  body.append('comparison_mode', comparisonMode)
  body.append('ai_consent', String(aiConsent))
  if (metadata.location?.trim()) body.append('location', metadata.location.trim())
  if (metadata.beforeDate) body.append('before_acquisition_date', metadata.beforeDate)
  if (metadata.afterDate) body.append('after_acquisition_date', metadata.afterDate)
  const response = await timedFetch(apiUrl('/api/analyze'), { method: 'POST', body })
  if (!response.ok) {
    const detail = await response.json().catch(() => null)
    throw new Error(detail?.detail ?? `Analysis failed (${response.status})`)
  }
  const result: unknown = await response.json()
  if (!result || typeof result !== 'object' || !('analysis_id' in result) || !('changed_pixels' in result) || !('changed_percent' in result) || !('regions' in result) || !('report' in result)) throw new Error('The API returned an invalid analysis result.')
  return result as AnalysisResult
}
