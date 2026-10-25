import { useState } from 'react'
import { analyzeImages } from '../services/api'
import type { AnalysisResult } from '../types/analysis'

export default function App() {
  const [before, setBefore] = useState<File | null>(null)
  const [after, setAfter] = useState<File | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!before || !after) return
    setBusy(true); setError(''); setResult(null)
    try { setResult(await analyzeImages(before, after)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to analyze these images.') }
    finally { setBusy(false) }
  }

  return <main className="min-h-screen bg-ink text-slate-100">
    <header className="border-b border-line px-8 py-5"><div className="mx-auto flex max-w-6xl items-center justify-between">
      <div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl border border-pulse/30 bg-pulse/10 text-pulse">◉</span><div><div className="font-semibold tracking-wide">ORBITAL<span className="text-pulse">PULSE</span></div><div className="text-xs text-slate-500">SATELLITE INTELLIGENCE</div></div></div>
      <span className="rounded-full border border-line px-3 py-1.5 text-xs text-slate-400">LOCAL ANALYSIS · AI OPTIONAL</span>
    </div></header>
    <section className="mx-auto max-w-6xl px-8 py-14">
      <p className="mb-3 text-xs font-semibold tracking-[.24em] text-pulse">ORCA CODER · SPACETECH</p>
      <h1 className="max-w-2xl text-4xl font-semibold leading-tight md:text-5xl">See what changed <span className="text-slate-500">on the ground.</span></h1>
      <p className="mt-4 max-w-xl text-slate-400">Compare two captures to surface changed areas and generate an explainable first-pass intelligence brief.</p>
      <div className="mt-10 grid gap-4 md:grid-cols-2">
        {[{ label: '01 / BASELINE IMAGE', file: before, set: setBefore }, { label: '02 / LATEST IMAGE', file: after, set: setAfter }].map((slot) => <label key={slot.label} className="cursor-pointer rounded-2xl border border-dashed border-slate-700 bg-panel p-6 transition hover:border-pulse/60">
          <span className="text-xs font-semibold tracking-widest text-slate-500">{slot.label}</span><div className="mt-8 text-3xl text-pulse">＋</div><div className="mt-3 font-medium">{slot.file?.name ?? 'Choose an image'}</div><div className="mt-1 text-sm text-slate-500">PNG, JPEG, or WebP · up to 20 MB</div>
          <input className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" onChange={e => slot.set(e.target.files?.[0] ?? null)} />
        </label>)}
      </div>
      <button disabled={!before || !after || busy} onClick={submit} className="mt-5 rounded-xl bg-pulse px-6 py-3 font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-40">{busy ? 'Analyzing imagery…' : 'Run change analysis →'}</button>
      {error && <p role="alert" className="mt-4 text-sm text-rose-300">{error}</p>}
      {result && <section className="mt-8 rounded-2xl border border-line bg-panel p-6" aria-live="polite"><div className="text-xs tracking-widest text-pulse">ANALYSIS COMPLETE · {result.analysis_id.slice(0, 8)}</div><h2 className="mt-3 text-2xl font-semibold">{result.changed_percent.toFixed(2)}% changed</h2><p className="mt-2 text-slate-400">{result.summary}</p><p className="mt-4 text-sm text-slate-500">{result.changed_pixels.toLocaleString()} of {result.total_pixels.toLocaleString()} pixels · {result.changed_regions} detected regions</p><p className="mt-4 border-t border-line pt-4 text-xs text-slate-500">Prototype CV signal only. Change detection does not establish cause or intent.</p></section>}
      <p className="mt-10 text-xs text-slate-600">Images are processed by the local API and stored temporarily on this machine.</p>
    </section>
  </main>
}
