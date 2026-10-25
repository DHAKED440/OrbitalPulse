import type { AnalysisResult, ApiHealth, AnalyzeMetadata, SampleImage, SampleScenario } from '../types/analysis'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')
const REQUEST_TIMEOUT_MS = 15_000
const ANALYSIS_TIMEOUT_MS = 120_000

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message)
    this.name = 'ApiError'
  }
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`
}

async function request(path: string, init: RequestInit = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(apiUrl(path), { ...init, signal: controller.signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(`The request timed out after ${Math.round(timeoutMs / 1000)} seconds. Try again or use smaller images.`)
    }
    throw new ApiError('Cannot reach the OrbitalPulse API. Check that FastAPI is running and the backend URL is correct.')
  } finally {
    window.clearTimeout(timeout)
  }
}

async function readJson(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new ApiError(`The API returned an invalid response (${response.status}).`, response.status)
  }
  try {
    return await response.json()
  } catch {
    throw new ApiError('The API response was not valid JSON.', response.status)
  }
}

async function responseError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status}).`
  try {
    const payload = await response.json() as { detail?: unknown }
    if (typeof payload.detail === 'string') message = payload.detail
    else if (Array.isArray(payload.detail)) message = payload.detail.map(item => record(item) && typeof item.msg === 'string' ? item.msg : '').filter(Boolean).join(' · ') || message
  } catch { /* Keep the status-based message for non-JSON errors. */ }
  return new ApiError(message, response.status)
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function parseAnalysisResult(value: unknown): AnalysisResult {
  if (!record(value)) throw new ApiError('The API returned an invalid analysis result.')
  const numeric = ['changed_percent', 'changed_pixels', 'total_pixels', 'image_width', 'image_height', 'changed_regions']
  if (typeof value.analysis_id !== 'string' || !value.analysis_id || numeric.some(key => typeof value[key] !== 'number' || !Number.isFinite(value[key]))) {
    throw new ApiError('The API analysis result is missing required metrics.')
  }
  if (typeof value.summary !== 'string' || typeof value.annotated_image_url !== 'string' || typeof value.report_url !== 'string' || !Array.isArray(value.regions)) {
    throw new ApiError('The API analysis result is missing its report or image artifacts.')
  }
  const regions = value.regions.map((region, index) => {
    if (!record(region) || typeof region.id !== 'string' || ['x', 'y', 'width', 'height', 'area_pixels'].some(key => typeof region[key] !== 'number' || !Number.isFinite(region[key]))) {
      throw new ApiError(`The API returned an invalid detected region at index ${index}.`)
    }
    return { id: region.id, x: region.x as number, y: region.y as number, width: region.width as number, height: region.height as number, area_pixels: region.area_pixels as number }
  })
  const integers = ['changed_pixels', 'total_pixels', 'image_width', 'image_height', 'changed_regions']
  if (typeof value.changed_percent !== 'number' || value.changed_percent < 0 || value.changed_percent > 100 ||
    integers.some(key => !Number.isInteger(value[key])) || (value.changed_pixels as number) < 0 || (value.total_pixels as number) < 1 ||
    (value.image_width as number) < 1 || (value.image_height as number) < 1 || (value.changed_regions as number) !== regions.length ||
    regions.some(region => region.x + region.width > (value.image_width as number) || region.y + region.height > (value.image_height as number) || !Number.isInteger(region.area_pixels)) ||
    (value.ai_analysis !== null && typeof value.ai_analysis !== 'string')) {
    throw new ApiError('The API returned out-of-range analysis values.')
  }
  for (const key of ['location', 'before_date', 'after_date']) {
    if (value[key] !== null && value[key] !== undefined && typeof value[key] !== 'string') throw new ApiError(`The API returned an invalid ${key} value.`)
  }
  return {
    analysis_id: value.analysis_id,
    changed_percent: value.changed_percent,
    changed_pixels: value.changed_pixels as number,
    total_pixels: value.total_pixels as number,
    image_width: value.image_width as number,
    image_height: value.image_height as number,
    summary: value.summary,
    changed_regions: value.changed_regions as number,
    regions,
    location: (value.location as string | null | undefined) ?? null,
    before_date: (value.before_date as string | null | undefined) ?? null,
    after_date: (value.after_date as string | null | undefined) ?? null,
    annotated_image_url: value.annotated_image_url,
    report_url: value.report_url,
    ai_analysis: value.ai_analysis as string | null,
  }
}

export async function getHealth(): Promise<ApiHealth> {
  const response = await request('/api/health')
  if (!response.ok) throw await responseError(response)
  const data = await readJson(response)
  if (!record(data) || data.status !== 'ok' || typeof data.vision_provider !== 'string') throw new ApiError('The API health response did not match the expected schema.')
  return { status: 'ok', vision_provider: data.vision_provider }
}

export async function listSamples(): Promise<SampleScenario[]> {
  const response = await request('/api/samples')
  if (!response.ok) throw await responseError(response)
  const data = await readJson(response)
  if (!Array.isArray(data)) throw new ApiError('The sample listing response was invalid.')
  return data.map((item, index) => {
    const validAsset = (asset: unknown) => record(asset) && typeof asset.filename === 'string' && typeof asset.url === 'string' && typeof asset.size_bytes === 'number' && typeof asset.media_type === 'string'
    if (!record(item) || typeof item.id !== 'string' || typeof item.title !== 'string' || typeof item.category !== 'string' || typeof item.description !== 'string' || typeof item.expected_change !== 'string' || typeof item.synthetic !== 'boolean' || !validAsset(item.before) || !validAsset(item.after)) {
      throw new ApiError(`The API returned an invalid sample entry at index ${index}.`)
    }
    return {
      id: item.id,
      title: item.title,
      category: item.category,
      description: item.description,
      expected_change: item.expected_change,
      synthetic: item.synthetic,
      before: item.before as SampleImage,
      after: item.after as SampleImage,
    }
  })
}

export async function getSampleFile(sample: SampleImage): Promise<File> {
  const response = await request(sample.url)
  if (!response.ok) throw await responseError(response)
  const blob = await response.blob()
  if (!blob.type.startsWith('image/')) throw new ApiError('The selected server sample is not a supported image.')
  return new File([blob], sample.filename, { type: sample.media_type })
}

export async function analyzeImages(before: File, after: File, metadata: AnalyzeMetadata = {}): Promise<AnalysisResult> {
  const body = new FormData()
  body.append('before_image', before, before.name)
  body.append('after_image', after, after.name)
  if (metadata.location?.trim()) body.append('location', metadata.location.trim())
  if (metadata.before_date) body.append('before_date', metadata.before_date)
  if (metadata.after_date) body.append('after_date', metadata.after_date)
  const response = await request('/api/analyze', { method: 'POST', body }, ANALYSIS_TIMEOUT_MS)
  if (!response.ok) throw await responseError(response)
  return parseAnalysisResult(await readJson(response))
}

export async function getReport(analysisId: string): Promise<AnalysisResult> {
  if (!/^[a-f0-9]{32}$/i.test(analysisId)) throw new ApiError('Invalid report identifier.')
  const response = await request(`/api/reports/${encodeURIComponent(analysisId)}`)
  if (!response.ok) throw await responseError(response)
  return parseAnalysisResult(await readJson(response))
}
