import { useEffect, useMemo, useState } from 'react'
import { analyzeImages } from '../services/api'
import type { AnalysisResult } from '../types/analysis'

type NavItem = 'Overview' | 'Analysis History' | 'Sample Scenarios' | 'Settings'
type Target = { id: string; severity: string; title: string; area: string; confidence: string; status: string; tone: 'critical' | 'moderate' | 'elevated' | 'low' }

const initialTargets: Target[] = [
  { id: 'REG-094-ALPHA', severity: 'CRITICAL', title: 'Rapid evaporation basin breach & brine surge', area: '1.14 km²', confidence: '98.4%', status: 'Unresolved hazard', tone: 'critical' },
  { id: 'REG-094-BETA', severity: 'MODERATE', title: 'Unpermitted road & pipeline excavation corridor', area: '0.68 km²', confidence: '94.1%', status: 'Validated', tone: 'moderate' },
  { id: 'REG-094-GAMMA', severity: 'ELEVATED', title: 'Ground subsidence & sub-surface moisture shift', area: '0.45 km²', confidence: '89.7%', status: 'Under review', tone: 'elevated' },
  { id: 'REG-094-DELTA', severity: 'LOW RISK', title: 'Seasonal surface salt crust crystallization bloom', area: '0.14 km²', confidence: '91.2%', status: 'Dismissed · natural cycle', tone: 'low' },
]

const Glyph = ({ children }: { children: string }) => <span className="glyph" aria-hidden="true">{children}</span>

export default function App() {
  const [before, setBefore] = useState<File | null>(null)
  const [after, setAfter] = useState<File | null>(null)
  const [previews, setPreviews] = useState<{ before: string; after: string } | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [pipelineOpen, setPipelineOpen] = useState(false)
  const [nav, setNav] = useState<NavItem>('Overview')
  const [mode, setMode] = useState('Dual-View')
  const [spectral, setSpectral] = useState('True Color (RGB)')
  const [gain, setGain] = useState(78)
  const [swipe, setSwipe] = useState(50)
  const [gridOn, setGridOn] = useState(true)
  const [targets, setTargets] = useState(initialTargets)
  const [notice, setNotice] = useState('')

  const changed = result?.changed_percent ?? 14.82
  const count = result?.changed_regions ?? 9
  const scenario = useMemo(() => previews ? 'CUSTOM IMAGE PAIR / LOCAL ANALYSIS' : nav === 'Sample Scenarios' ? 'SAMPLE SCENARIOS / ATACAMA SALAR' : 'SAMPLE MISSION / SALAR-DELTA-094', [nav, previews])
  const displayedTargets: Target[] = result ? [{ id: result.analysis_id.slice(0, 8).toUpperCase(), severity: 'CANDIDATE', title: result.summary, area: 'Not georeferenced', confidence: 'N/A', status: 'Pixel signal · cause unclassified', tone: 'moderate' }] : targets

  useEffect(() => {
    if (!before || !after) { setPreviews(null); return }
    const beforeUrl = URL.createObjectURL(before)
    const afterUrl = URL.createObjectURL(after)
    setPreviews({ before: beforeUrl, after: afterUrl })
    setSpectral('True Color (RGB)')
    return () => { URL.revokeObjectURL(beforeUrl); URL.revokeObjectURL(afterUrl) }
  }, [before, after])

  async function submit() {
    if (!before || !after) { setUploadOpen(true); return }
    setBusy(true); setError(''); setNotice('')
    try {
      const data = await analyzeImages(before, after)
      setResult(data); setUploadOpen(false); setNotice(`Analysis ${data.analysis_id.slice(0, 8)} complete`)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to analyze these images.') }
    finally { setBusy(false) }
  }

  function exportReport() {
    const report = result ?? { analysis_id: 'DEMO-SALAR-094', changed_percent: changed, changed_pixels: 14230, total_pixels: 96000, summary: 'Sample scenario report. Run an analysis with your images to replace these metrics.', changed_regions: count, ai_analysis: null }
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }))
    const link = document.createElement('a'); link.href = url; link.download = `orbitalpulse-${report.analysis_id}.json`; link.click(); URL.revokeObjectURL(url)
  }

  function closeTarget(id: string) { setTargets(items => items.filter(item => item.id !== id)); setNotice(`${id} removed from active triage`) }

  return <div className="workstation">
    <header className="topbar">
      <div className="brand-block"><span className="brand-mark">◉</span><span><b>ORBITAL<span>PULSE</span></b><small>GEO-INT PLATFORM</small></span></div>
      <div className="topbar-content">
        <div className="crumb"><span className="chip chip-lime">{previews ? 'LOCAL' : 'SAMPLE'}</span><span>{previews ? result?.analysis_id.slice(0, 16).toUpperCase() ?? 'NEW-IMAGE-PAIR' : 'ANOMALY-SURFACE-DELTA-094'}</span><i>//</i><span className="muted">{previews ? 'USER-IMAGES' : 'ATACAMA-SALAR-BASIN'}</span></div>
        <div className="system-state"><span className="chip"><i className="dot dot-sage" /> LOCAL CV PIPELINE</span><span className="chip">AI PROVIDER DISABLED</span><span className="top-separator" /><button className="icon-button" aria-label="Notifications" onClick={() => setNotice('No new mission alerts')}><Glyph>♧</Glyph></button><span className="utc-clock"><i className="dot dot-lime" /> LOCAL SESSION</span><span className="analyst"><b>ANALYST CONSOLE</b><small>Mission workspace</small></span><span className="avatar">OP</span></div>
      </div>
    </header>

    <aside className="sidebar">
      <div><div className="nav-caption">MISSION OPERATIONS</div>
        <button className={`nav-item ${nav === 'Overview' ? 'active' : ''}`} onClick={() => setNav('Overview')}><Glyph>◈</Glyph><span>Overview</span></button>
        <button className="nav-item nav-new" onClick={() => { setNav('Overview'); setUploadOpen(true) }}><Glyph>⊕</Glyph><span>New Analysis</span></button>
        <button className={`nav-item ${nav === 'Analysis History' ? 'active' : ''}`} onClick={() => { setNav('Analysis History'); setNotice(result ? `Latest run: ${result.analysis_id.slice(0, 8)}` : 'No saved analyses in this session yet') }}><Glyph>◴</Glyph><span>Analysis History</span><b className="nav-count">{result ? '01' : '24'}</b></button>
        <button className={`nav-item ${nav === 'Sample Scenarios' ? 'active' : ''}`} onClick={() => setNav('Sample Scenarios')}><Glyph>⌗</Glyph><span>Sample Scenarios</span><b className="nav-live">4 LIVE</b></button>
        <button className={`nav-item ${nav === 'Settings' ? 'active' : ''}`} onClick={() => { setNav('Settings'); setPipelineOpen(true) }}><Glyph>☷</Glyph><span>Settings</span></button>
      </div>
      <div className="telemetry-card"><div className="telemetry-head"><span><i className="dot dot-lime" /> WORKSTATION</span><b>READY</b></div><div><span>MODE</span><b>LOCAL CV</b></div><div><span>AI</span><b>OPTIONAL / OFF</b></div><div><span>INPUT</span><b>{previews ? '2 IMAGES' : 'SAMPLE SCENE'}</b></div></div>
    </aside>

    <main className="main-area">
      <section className="mission-heading">
        <div className="mission-copy"><div className="mission-meta"><span className="chip chip-lime"><i className="dot dot-lime" /> {scenario}</span><span className="coordinates">{previews ? 'CUSTOM INPUT · GEOLOCATION METADATA UNAVAILABLE' : 'LAT: -23.8206° &nbsp;|&nbsp; LON: -68.2396° · SAMPLE'}</span></div><h1>Earth changes. Decoded.</h1><p>Compare satellite and aerial captures, investigate pixel-level changes, and prepare an explainable brief for analyst review.</p></div>
        <div className="main-actions"><button className="button button-secondary" onClick={() => setPipelineOpen(true)}><Glyph>☷</Glyph> Configure AI Pipeline</button><button className="button button-secondary" onClick={exportReport}><Glyph>⇩</Glyph> Export Report</button><button className="button button-primary" onClick={submit} disabled={busy}><Glyph>⊞</Glyph> {busy ? 'Analyzing…' : 'Run Change Detection'} <small>LOCAL CV</small></button></div>
      </section>
      {notice && <div className="notice" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss">×</button></div>}

      <section className="viewer-card">
        <div className="viewer-toolbar">
          <div className="toolbar-row"><div className="segmented">{['Dual-View', 'Difference Map', 'Vector Polygons', 'Swipe Slider'].map(item => <button key={item} className={mode === item ? 'selected' : ''} onClick={() => setMode(item)}>{item}</button>)}</div><div className="viewer-actions">{mode === 'Swipe Slider' && previews && <><span className="spectral-label">SWIPE</span><input aria-label="Swipe comparison position" type="range" min="5" max="95" value={swipe} onChange={e => setSwipe(Number(e.target.value))} /><span className="gain-value">{swipe}%</span></>}<span className="spectral-label">ANOMALY GAIN</span><input aria-label="Anomaly gain" type="range" min="0" max="100" value={gain} onChange={e => setGain(Number(e.target.value))} /><span className="gain-value">{(gain / 100).toFixed(2)}σ</span><button className={`icon-button ${gridOn ? 'icon-active' : ''}`} title="Toggle reticle grid" onClick={() => setGridOn(!gridOn)}><Glyph>▦</Glyph></button><button className="icon-button" title="Recenter target" onClick={() => setNotice('View centered on target REG-094-ALPHA')}><Glyph>◎</Glyph></button><button className="icon-button" title="Fullscreen canvas" onClick={() => document.querySelector('.map-viewport')?.requestFullscreen?.()}><Glyph>⛶</Glyph></button></div></div>
          <div className="toolbar-row second-row"><div className="spectral-switch"><b>SPECTRAL:</b>{['True Color (RGB)', 'NIR / SWIR False', 'NDVI'].map(item => <button key={item} className={spectral === item ? 'selected' : ''} disabled={Boolean(previews && item !== 'True Color (RGB)')} title={previews && item !== 'True Color (RGB)' ? 'RGB uploads do not contain these spectral bands' : undefined} onClick={() => setSpectral(item)}>{item}</button>)}</div><span className="map-source">{previews ? 'USER UPLOADS · RGB PREVIEW' : 'SAMPLE · SENTINEL-2C / WORLDVIEW-3'}</span></div>
        </div>
        <div className={`map-viewport mode-${mode.toLowerCase().replaceAll(' ', '-')} spectral-${spectral.startsWith('NIR') ? 'nir' : spectral === 'NDVI' ? 'ndvi' : 'rgb'} ${gridOn ? 'grid-on' : ''} ${previews ? 'uploaded-scene' : ''}`}>
          {previews ? mode === 'Swipe Slider' ? <div className="uploaded-swipe"><img src={previews.before} alt={`Baseline image: ${before?.name ?? ''}`} /><div className="swipe-after" style={{ clipPath: `inset(0 0 0 ${swipe}%)` }}><img src={previews.after} alt={`Latest image: ${after?.name ?? ''}`} /></div><span className="uploaded-divider" style={{ left: `${swipe}%` }} /></div> : <div className="uploaded-pair"><div><img src={previews.before} alt={`Baseline image: ${before?.name ?? ''}`} /></div><div><img src={previews.after} alt={`Latest image: ${after?.name ?? ''}`} /></div><span className="uploaded-divider" /></div> : <img src="/samples/atacama-comparison.png" alt="Atacama salt basin sample comparison with marked candidate regions" />}
          <div className="map-caption caption-left"><i className="dot dot-sage" /><div><b>T0: BASELINE ACQUISITION</b><small>{previews ? before?.name : '2024-04-12 09:24:18 UTC · SENTINEL-2C (MSI 10m GSD)'}</small></div></div>
          <div className="map-caption caption-right"><i className="dot dot-coral" /><div><b>T1: {previews ? 'LATEST IMAGE' : 'SAMPLE OBSERVATION'}</b><small>{previews ? after?.name : '2024-10-28 09:18:02 UTC · WORLDVIEW-3 (0.3m RESAMPLED)'}</small></div>{!previews && <em>Δ 18D</em>}</div>
          {mode === 'Vector Polygons' && <div className="vector-overlay">{previews ? 'VECTOR OUTPUT UNAVAILABLE · NO GEOREFERENCING' : 'ILLUSTRATIVE SAMPLE POLYGONS'}</div>}
          {mode === 'Difference Map' && previews && <div className="vector-overlay">VISUAL FILTER PREVIEW · MASK EXPORT NOT AVAILABLE</div>}
          {!previews && <div className="map-badge"><i className="dot dot-coral" /> SAMPLE ANOMALY OVERLAY</div>}
          <div className="map-corner">{previews ? 'UNREGISTERED RGB' : 'SAMPLE OVERLAY'} <span>{previews ? 'NO GCP DATA' : '200 m / 656 ft'}</span></div>
        </div>
        <div className="viewer-foot">{previews ? <><span>USER IMAGES · RGB PREVIEW</span><span>ACQUISITION METADATA NOT PROVIDED</span><span className="foot-right">LOCAL COMPARISON</span></> : <><span>CLOUD: 0.02% · SAMPLE</span><span>SUN ELEV: 58.4°</span><span>OFF-NADIR: 4.1°</span><span className="foot-right">SAMPLE SCENARIO · ATACAMA SALAR</span></>}</div>
      </section>

      <section className="metrics-grid" aria-label="Analysis metrics">
        <article className="metric-card"><div className="metric-label">CHANGED PIXELS <Glyph>⌁</Glyph></div><div className="metric-value lime">{changed.toFixed(2)}% <small>{result ? 'measured' : 'sample scene'}</small></div><div className="metric-foot"><span>{result ? `${result.changed_pixels.toLocaleString()} pixels above threshold` : 'Atacama demo comparison'}</span><span>{result ? `${result.total_pixels.toLocaleString()} total` : 'illustrative values'}</span></div></article>
        <article className="metric-card"><div className="metric-label">CANDIDATE REGIONS <Glyph>◉</Glyph></div><div className="severity-pills">{result ? <><b>{count} CANDIDATE</b><span>CAUSE UNASSESSED</span></> : <><b>3 HIGH</b><span>4 MOD</span><span>2 LOW</span></>}</div><div className="metric-foot"><span>{result ? `${count} connected regions` : '9 illustrative clusters'}</span><span>{result ? 'Thresholded pixels' : 'Sample triage'}</span></div></article>
        <article className="metric-card"><div className="metric-label">IMAGE DIMENSIONS <Glyph>◎</Glyph></div><div className="metric-value">{result ? 'RESIZED' : 'SAMPLE'} <small className="lock-tag">LOCAL</small></div><div className="metric-foot"><span>Pixel dimensions aligned</span><span>No GCP<br />registration</span></div></article>
        <article className="metric-card"><div className="metric-label">VISION MODEL <Glyph>ϟ</Glyph></div><div className="metric-value lime">OPTIONAL</div><div className="metric-foot"><span>Local CV path<br />available</span><span>Provider<br />not configured</span></div></article>
      </section>

      <section className="analysis-grid">
        <article className="panel triage-panel"><header className="panel-header"><h2><Glyph>▤</Glyph> Region Explorer &amp; Candidate Review</h2><span className="chip chip-lime">{result ? '1 LOCAL RESULT' : `${targets.length} SAMPLE TARGETS`}</span><button className="sort-button" onClick={() => setTargets(items => [...items].reverse())}>Sort: Severity ↓</button><button className="icon-button" onClick={() => setTargets(initialTargets)} title="Reset sample targets"><Glyph>▽</Glyph></button></header>
          <div className="target-list">{displayedTargets.map(target => <article key={target.id} className={`target-row ${target.tone}`}><div className="target-top"><span className={`severity-tag ${target.tone}`}>{target.severity} // {target.id}</span><span className="confidence">{target.confidence} <small>{result ? 'Model confidence unavailable' : 'Sample confidence'}</small></span><i className={`dot dot-${target.tone === 'critical' ? 'coral' : target.tone === 'moderate' ? 'amber' : 'sage'}`} /></div><h3>{target.title}</h3><div className="target-meta"><span>AREA: <b>{target.area}</b></span><span>·</span><span>{result ? 'COORDS: UNAVAILABLE · NO GEOLOCATION METADATA' : 'COORDS: -23.8214°, -68.2391° · SAMPLE'}</span></div><div className="target-bottom"><span>STATUS: {target.status}</span><div><button className="mini-button" onClick={() => setNotice(`Reviewing ${target.id} · inspect source imagery and metadata`)}><Glyph>⌕</Glyph> Inspect</button>{result ? <button className="mini-button" onClick={() => setResult(null)}>Clear result</button> : <button className="mini-button" onClick={() => closeTarget(target.id)}>{target.tone === 'low' ? 'Archive' : 'Dismiss'}</button>}</div></div></article>)}</div>
        </article>

        <article className="panel assessment-panel"><header className="panel-header"><h2><Glyph>♧</Glyph> Change Interpretation</h2><span className="chip chip-lime">LOCAL CV MODE</span></header><div className="assessment-body"><div className="conclusion"><span className="section-label">SYNTHESIS CONCLUSION</span><h3>{result ? 'Image change signal for analyst review' : 'Atacama sample · candidate surface change'}</h3><p>{result ? result.summary : 'The illustrative sample marks candidate change areas in a salt basin. This dashboard uses local pixel comparison; confirm image alignment and context before interpreting the cause.'}</p></div><div className="section-label evidence-title">OBSERVED IMAGE EVIDENCE</div><div className="evidence-item"><i className="evidence-icon coral">≈</i><p><b>Pixel Difference:</b> {result ? 'Pixels above the backend threshold are included in this change summary.' : 'The sample marks a visible reflectance difference for demonstration.'}</p></div><div className="evidence-item"><i className="evidence-icon sage">⌁</i><p><b>Region Grouping:</b> {result ? `${result.changed_regions} connected candidate regions` : 'Nine illustrative clusters'} flagged for visual inspection.</p></div><div className="evidence-item"><i className="evidence-icon amber">◷</i><p><b>Temporal Context:</b> Sample dates and sensor details are illustrative; uploaded images do not include this context.</p></div><div className="section-label hypothesis-title">FOLLOW-UP CHECKS</div><div className="hypothesis"><div><span>Geospatial co-registration</span><b className="sage-text">REQUIRED</b></div><div className="progress-track"><i style={{ width: '68%' }} /></div><small>Current prototype resizes images; it does not register geographic coordinates.</small></div><div className="hypothesis"><div><span>Cause classification</span><b className="amber-text">UNRESOLVED</b></div><div className="progress-track amber-track"><i style={{ width: '34%' }} /></div><small>Pixel change alone cannot distinguish natural and human activity.</small></div><button className="dossier-button" onClick={exportReport}><Glyph>▤</Glyph><span>Export change summary<br /><small>JSON · Analyst review</small></span><b>→</b></button></div></article>
      </section>

      {error && <div className="toast error-toast" role="alert">{error}<button onClick={() => setError('')}>×</button></div>}
    </main>

    {uploadOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setUploadOpen(false) }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><header><div><span className="section-label">NEW MISSION ANALYSIS</span><h2 id="upload-title">Add acquisition pair</h2></div><button className="icon-button" onClick={() => setUploadOpen(false)} aria-label="Close">×</button></header><p className="modal-copy">Select baseline and latest captures. The local CV pipeline compares them without an external AI service.</p><div className="file-slots">{[{ label: 'T0 / BASELINE CAPTURE', file: before, set: setBefore }, { label: 'T1 / LATEST CAPTURE', file: after, set: setAfter }].map(slot => <label key={slot.label} className="file-slot"><span className="section-label">{slot.label}</span><span className="file-plus">＋</span><b>{slot.file?.name ?? 'Choose image'}</b><small>PNG, JPEG, or WebP · up to 20 MB</small><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => slot.set(e.target.files?.[0] ?? null)} /></label>)}</div>{error && <p className="modal-error" role="alert">{error}</p>}<footer><span>Images remain on this local workstation.</span><button className="button button-primary" onClick={submit} disabled={!before || !after || busy}>{busy ? 'Analyzing…' : 'Run local comparison →'}</button></footer></section></div>}

    {pipelineOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setPipelineOpen(false) }}><section className="modal pipeline-modal" role="dialog" aria-modal="true" aria-labelledby="pipeline-title"><header><div><span className="section-label">PROCESSING CONFIGURATION</span><h2 id="pipeline-title">AI pipeline</h2></div><button className="icon-button" onClick={() => setPipelineOpen(false)} aria-label="Close">×</button></header><div className="pipeline-setting"><div><b>Local image comparison</b><span>OpenCV absolute difference · always available</span></div><span className="chip chip-lime">ACTIVE</span></div><div className="pipeline-setting"><div><b>Vision model provider</b><span>External provider is not configured</span></div><span className="chip">DISABLED</span></div><div className="pipeline-setting"><div><b>Anomaly gain threshold</b><span>Adjust sensitivity of changed pixel detection</span></div><input type="range" min="0" max="100" value={gain} onChange={e => setGain(Number(e.target.value))} /></div><p className="modal-copy">Current backend uses a fixed pixel threshold. Gain is a dashboard control for this prototype; provider analysis and causal classification are not enabled.</p><footer><span>Configuration is local to this session.</span><button className="button button-primary" onClick={() => setPipelineOpen(false)}>Done</button></footer></section></div>}
  </div>
}
