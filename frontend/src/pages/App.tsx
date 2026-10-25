import { useEffect, useMemo, useState } from 'react'
import { analyzeImages } from '../services/api'
import type { AnalysisResult } from '../types/analysis'

type NavItem = 'Overview' | 'New Analysis' | 'Analysis History' | 'Intelligence Report' | 'Sample Scenarios' | 'Settings'
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
  const [comparisonMode, setComparisonMode] = useState<'registered' | 'original'>('registered')
  const [aiConsent, setAiConsent] = useState(false)
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
    setResult(null)
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
      const data = await analyzeImages(before, after, comparisonMode, aiConsent)
      setResult(data); setUploadOpen(false); setNotice(`Analysis ${data.analysis_id.slice(0, 8)} complete`)
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to analyze these images.') }
    finally { setAiConsent(false); setBusy(false) }
  }

  function exportReport() {
    if (!result) { setNotice('Run an analysis before downloading its report.'); return }
    window.location.assign(`/api/report/${result.analysis_id}/download?format=json`)
  }

  function closeTarget(id: string) { setTargets(items => items.filter(item => item.id !== id)); setNotice(`${id} removed from active triage`) }

  return <div className="workstation">
    <header className="topbar">
      <div className="brand-block"><span className="brand-mark">◉</span><span><b>ORBITAL<span>PULSE</span></b><small>GEO-INT PLATFORM</small></span></div>
      <div className="topbar-content">
        <div className="crumb"><span className="chip chip-lime">{nav === 'Intelligence Report' ? 'REPORT' : previews ? 'LOCAL' : 'SAMPLE'}</span><span>{nav === 'Intelligence Report' ? result ? `IR-${result.analysis_id.slice(0, 12).toUpperCase()}` : 'DRAFT-SALAR-094' : previews ? result?.analysis_id.slice(0, 16).toUpperCase() ?? 'NEW-IMAGE-PAIR' : 'ANOMALY-SURFACE-DELTA-094'}</span><i>//</i><span className="muted">{previews ? 'USER-IMAGES' : 'ATACAMA-SALAR-BASIN'}</span></div>
        <div className="system-state"><span className="chip"><i className="dot dot-sage" /> LOCAL CV PIPELINE</span><span className="chip">AI PROVIDER DISABLED</span><span className="top-separator" /><button className="icon-button" aria-label="Notifications" onClick={() => setNotice('No new mission alerts')}><Glyph>♧</Glyph></button><span className="utc-clock"><i className="dot dot-lime" /> LOCAL SESSION</span><span className="analyst"><b>ANALYST CONSOLE</b><small>Mission workspace</small></span><span className="avatar">OP</span></div>
      </div>
    </header>

    <aside className="sidebar">
      <div><div className="nav-caption">MISSION OPERATIONS</div>
        <button className={`nav-item ${nav === 'Overview' ? 'active' : ''}`} onClick={() => setNav('Overview')}><Glyph>◈</Glyph><span>Overview</span></button>
        <button className={`nav-item nav-new ${nav === 'New Analysis' ? 'active' : ''}`} onClick={() => setNav('New Analysis')}><Glyph>⊕</Glyph><span>New Analysis</span></button>
        <button className={`nav-item ${nav === 'Analysis History' ? 'active' : ''}`} onClick={() => { setNav('Analysis History'); setNotice(result ? `Latest run: ${result.analysis_id.slice(0, 8)}` : 'No saved analyses in this session yet') }}><Glyph>◴</Glyph><span>Analysis History</span><b className="nav-count">{result ? '01' : '24'}</b></button>
        <button className={`nav-item ${nav === 'Intelligence Report' ? 'active' : ''}`} onClick={() => setNav('Intelligence Report')}><Glyph>▤</Glyph><span>Intelligence Report</span></button>
        <button className={`nav-item ${nav === 'Sample Scenarios' ? 'active' : ''}`} onClick={() => setNav('Sample Scenarios')}><Glyph>⌗</Glyph><span>Sample Scenarios</span><b className="nav-live">4 LIVE</b></button>
        <button className={`nav-item ${nav === 'Settings' ? 'active' : ''}`} onClick={() => { setNav('Settings'); setPipelineOpen(true) }}><Glyph>☷</Glyph><span>Settings</span></button>
      </div>
      <div className="telemetry-card"><div className="telemetry-head"><span><i className="dot dot-lime" /> WORKSTATION</span><b>READY</b></div><div><span>MODE</span><b>LOCAL CV</b></div><div><span>AI</span><b>OPTIONAL / OFF</b></div><div><span>INPUT</span><b>{previews ? '2 IMAGES' : 'SAMPLE SCENE'}</b></div></div>
    </aside>

    <main className="main-area">
      {nav === 'New Analysis' ? <ComparisonWorkbench before={before} after={after} previews={previews} result={result} busy={busy} error={error} comparisonMode={comparisonMode} onComparisonModeChange={setComparisonMode} aiConsent={aiConsent} onAiConsentChange={setAiConsent} onRun={submit} onUpload={() => setUploadOpen(true)} onExport={exportReport} /> : nav === 'Intelligence Report' ? <IntelligenceReport before={before} after={after} previews={previews} result={result} onExport={exportReport} onCompare={() => setNav('New Analysis')} onConfigure={() => setPipelineOpen(true)} /> : <>
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
      </>}
    </main>

    {uploadOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setUploadOpen(false) }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title"><header><div><span className="section-label">NEW MISSION ANALYSIS</span><h2 id="upload-title">Add acquisition pair</h2></div><button className="icon-button" onClick={() => setUploadOpen(false)} aria-label="Close">×</button></header><p className="modal-copy">Select baseline and latest captures. The local CV pipeline compares them without an external AI service.</p><div className="file-slots">{[{ label: 'T0 / BASELINE CAPTURE', file: before, set: setBefore }, { label: 'T1 / LATEST CAPTURE', file: after, set: setAfter }].map(slot => <label key={slot.label} className="file-slot"><span className="section-label">{slot.label}</span><span className="file-plus">＋</span><b>{slot.file?.name ?? 'Choose image'}</b><small>PNG, JPEG, or WebP · up to 20 MB</small><input type="file" accept="image/png,image/jpeg,image/webp" onChange={e => slot.set(e.target.files?.[0] ?? null)} /></label>)}</div>{error && <p className="modal-error" role="alert">{error}</p>}<footer><span>Images remain on this local workstation.</span><button className="button button-primary" onClick={submit} disabled={!before || !after || busy}>{busy ? 'Analyzing…' : 'Run local comparison →'}</button></footer></section></div>}

    {pipelineOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setPipelineOpen(false) }}><section className="modal pipeline-modal" role="dialog" aria-modal="true" aria-labelledby="pipeline-title"><header><div><span className="section-label">PROCESSING CONFIGURATION</span><h2 id="pipeline-title">AI pipeline</h2></div><button className="icon-button" onClick={() => setPipelineOpen(false)} aria-label="Close">×</button></header><div className="pipeline-setting"><div><b>Local image comparison</b><span>OpenCV absolute difference · always available</span></div><span className="chip chip-lime">ACTIVE</span></div><div className="pipeline-setting"><div><b>Vision model provider</b><span>External provider is not configured</span></div><span className="chip">DISABLED</span></div><div className="pipeline-setting"><div><b>Anomaly gain threshold</b><span>Adjust sensitivity of changed pixel detection</span></div><input type="range" min="0" max="100" value={gain} onChange={e => setGain(Number(e.target.value))} /></div><p className="modal-copy">Current backend uses a fixed pixel threshold. Gain is a dashboard control for this prototype; provider analysis and causal classification are not enabled.</p><footer><span>Configuration is local to this session.</span><button className="button button-primary" onClick={() => setPipelineOpen(false)}>Done</button></footer></section></div>}
  </div>
}

type WorkbenchProps = {
  before: File | null
  after: File | null
  previews: { before: string; after: string } | null
  result: AnalysisResult | null
  busy: boolean
  error: string
  comparisonMode: 'registered' | 'original'
  onComparisonModeChange: (mode: 'registered' | 'original') => void
  aiConsent: boolean
  onAiConsentChange: (consent: boolean) => void
  onRun: () => void | Promise<void>
  onUpload: () => void
  onExport: () => void
}

const sampleRegions = [
  { id: 'REG-01', name: 'Lithium Dike Rupture', confidence: '98.4%', severity: 'CRITICAL', area: '1.14 km²' },
  { id: 'REG-02', name: 'Access Corridor', confidence: '88.1%', severity: 'MODERATE', area: '0.68 km²' },
  { id: 'REG-03', name: 'Brine Flux Wetland', confidence: '92.5%', severity: 'ELEVATED', area: '0.45 km²' },
  { id: 'REG-04', name: 'Shadow Flux', confidence: '64.2%', severity: 'LOW', area: '0.14 km²' },
]

function ComparisonWorkbench({ before, after, previews, result, busy, error, comparisonMode, onComparisonModeChange, aiConsent, onAiConsentChange, onRun, onUpload, onExport }: WorkbenchProps) {
  const [view, setView] = useState('Dual-Swipe')
  const [swipe, setSwipe] = useState(50)
  const [zoom, setZoom] = useState(1)
  const [blinkAfter, setBlinkAfter] = useState(false)
  const [selected, setSelected] = useState('REG-01')
  const [notice, setNotice] = useState('')
  const region = sampleRegions.find(item => item.id === selected) ?? sampleRegions[0]

  useEffect(() => {
    if (view !== 'Blink' || !previews) { setBlinkAfter(false); return }
    const interval = window.setInterval(() => setBlinkAfter(value => !value), 750)
    return () => window.clearInterval(interval)
  }, [view, previews])

  const openComparison = () => {
    if (view === 'Blink' && previews) return <img className="workbench-sample" src={blinkAfter ? previews.after : previews.before} alt={blinkAfter ? 'Latest uploaded image' : 'Baseline uploaded image'} />
    if (previews && view === 'Dual-Swipe') return <div className="workbench-swipe"><img className="workbench-before" src={previews.before} alt={`Baseline image ${before?.name ?? ''}`} /><div className="workbench-after" style={{ clipPath: `inset(0 0 0 ${swipe}%)` }}><img src={previews.after} alt={`Latest image ${after?.name ?? ''}`} /></div><span className="workbench-divider" style={{ left: `${swipe}%` }} /></div>
    if (previews) return <div className="workbench-pair"><div><img src={previews.before} alt={`Baseline image ${before?.name ?? ''}`} /></div><div><img src={previews.after} alt={`Latest image ${after?.name ?? ''}`} /></div></div>
    return <img className="workbench-sample" src="/samples/atacama-workbench.png" alt="Illustrative Atacama satellite comparison with sample change regions" />
  }

  return <div className="comparison-workbench">
    <div className="workbench-topline"><div><span className="section-label">{previews ? 'CUSTOM IMAGE PAIR' : 'AOI-8492 / SAMPLE SCENARIO'}</span><b>{previews ? 'LOCAL IMAGE COMPARISON' : 'SALAR DE ATACAMA · LITHIUM EVAPORATION SECTOR 4'}</b></div><div className="workbench-synthesis"><span>{previews ? 'RGB INPUTS · GEOLOCATION UNKNOWN' : 'SAMPLE BAND SYNTHESIS · RGB / SWIR COMPOSITE'}</span><b className="cv-status"><i className="dot dot-sage" /> LOCAL CV {result ? 'COMPLETE' : 'READY'}</b></div></div>
    <div className="workbench-modebar"><div className="mode-tabs">{['Dual-Swipe', 'Diff Heatmap', 'Vector Overlay', 'Blink'].map(item => <button key={item} className={view === item ? 'selected' : ''} onClick={() => setView(item)}>{item}</button>)}</div><div className="modebar-right">{view === 'Dual-Swipe' && previews && <label className="swipe-control">SWIPE <input aria-label="Image reveal position" type="range" min="5" max="95" value={swipe} onChange={e => setSwipe(Number(e.target.value))} /> {swipe}%</label>}<label className="swipe-control">COMPARE <select value={comparisonMode} onChange={event => onComparisonModeChange(event.target.value as 'registered' | 'original')}><option value="registered">Registered</option><option value="original">Original</option></select></label><button className="button button-primary workbench-run" onClick={onRun} disabled={busy}>{busy ? 'Analyzing…' : result ? 'Run Again' : 'Run Change Detection'}</button></div></div>
    <label className="consent-note"><input type="checkbox" checked={aiConsent} onChange={event => onAiConsentChange(event.target.checked)} /> I consent to sending these images and selected region crops to OpenAI for semantic analysis. Unchecked by default; computer-vision analysis remains local.</label>

    <div className="comparison-layout">
      <section className={`comparison-view view-${view.toLowerCase().replaceAll(' ', '-')} ${previews ? 'has-uploads' : 'sample-view'}`}>
        <div className="compare-canvas"><div className="compare-art" style={{ transform: `scale(${zoom})` }}>{openComparison()}</div>
          <div className="capture-label capture-before"><i className="dot dot-sage" /><div><b>T0 · BEFORE CAPTURE</b><small>{previews ? before?.name : '2024-04-12 09:14 UTC · SENTINEL-2C · SAMPLE'}</small></div></div>
          <div className="capture-label capture-after"><i className="dot dot-lime" /><div><b>T1 · AFTER CAPTURE</b><small>{previews ? after?.name : '2024-10-28 10:22 UTC · WORLDVIEW-3 · SAMPLE'}</small></div></div>
          {view === 'Diff Heatmap' && <div className="map-mode-note">{result ? 'METRICS AVAILABLE · SPATIAL MASK NOT RETURNED BY API' : 'ILLUSTRATIVE SAMPLE HEATMAP VIEW'}</div>}
          {view === 'Vector Overlay' && <div className="map-mode-note">{previews ? 'VECTOR OUTPUT NEEDS GEOREFERENCED IMAGERY' : 'SAMPLE VECTOR ANNOTATIONS · NOT COMPUTED FROM UPLOADS'}</div>}
          {view === 'Blink' && previews && <div className="blink-indicator">BLINK · {blinkAfter ? 'T1' : 'T0'}</div>}
          {!previews && <div className="canvas-coordinates">23°49′14.28″S&nbsp; 68°14′22.04″W · 2,341m ELEV · SAMPLE</div>}
          <div className="canvas-zoom"><button aria-label="Zoom in" onClick={() => setZoom(value => Math.min(1.6, value + .1))}>＋</button><button aria-label="Zoom out" onClick={() => setZoom(value => Math.max(1, value - .1))}>−</button><span>{Math.round(zoom * 100)}%</span><button aria-label="Reset zoom" onClick={() => setZoom(1)}>⛶</button></div>
        </div>
        <div className="layer-controls"><span className="layer-heading">DISPLAY LAYERS</span><label title="Bounding boxes are part of the sample scene"><input type="checkbox" checked readOnly disabled /> Bounding Boxes <b>{previews ? 'UNAVAILABLE' : 'SAMPLE'}</b></label><label title="The current API returns summary metrics, not an image mask"><input type="checkbox" disabled /> Change Mask <b>API PENDING</b></label><label><input type="checkbox" disabled /> Contours</label><label><input type="checkbox" disabled /> Thermal IR</label><span className="layer-note">Local API returns pixel metrics; geospatial overlays are not generated.</span></div>
        <div className="canvas-status"><span>RGB PREVIEW</span><span>{previews ? 'ACQUISITION METADATA UNAVAILABLE' : 'SAMPLE · CLOUD 0.00% · GSD 0.31m/px'}</span><span className="canvas-status-right">{result ? `${result.changed_percent.toFixed(2)}% PIXEL CHANGE` : 'SAMPLE SCENE'}</span></div>
      </section>

      <aside className="region-inspector">
        <div className="inspector-header"><span><Glyph>⌖</Glyph> REGION INSPECTOR</span><b>{result ? 'LOCAL RESULT' : 'SAMPLE'}</b></div>
        {result ? <>
          <div className="inspector-title"><small>ANALYSIS · {result.analysis_id.slice(0, 8).toUpperCase()}</small><h2>Change candidates</h2><span className="risk-chip moderate">PIXEL SIGNAL · CAUSE UNASSESSED</span></div>
          <section className="inspector-card"><h3>LOCAL CHANGE METRICS <span>NO GEOREFERENCE</span></h3><div className="inspector-stats"><div><small>PIXELS CHANGED</small><b>{result.changed_pixels.toLocaleString()}</b></div><div><small>IMAGE PIXELS</small><b>{result.total_pixels.toLocaleString()}</b></div><div><small>AREA DELTA</small><b>{result.changed_percent.toFixed(2)}%</b></div><div><small>CONNECTED REGIONS</small><b>{result.changed_regions}</b></div></div></section>
          <section className="inspector-card"><h3>CV SUMMARY</h3><p>{result.summary}</p><small className="inspector-disclaimer">Grayscale absolute difference with a fixed threshold. This result does not classify causes or provide vector polygons.</small></section>
        </> : <>
          <div className="inspector-title"><small>{region.id} · SELECTED SAMPLE REGION</small><h2>{region.name}</h2><span className="risk-chip critical"><i className="dot dot-coral" /> SAMPLE CRITICAL HAZARD <b>{region.confidence} SAMPLE</b></span></div>
          <section className="inspector-card"><h3>REGION SELECTION <span>ILLUSTRATIVE</span></h3><div className="region-selector">{sampleRegions.map(item => <button key={item.id} className={selected === item.id ? 'selected' : ''} onClick={() => setSelected(item.id)}><b>{item.id}</b><span>{item.name}</span><small>{item.confidence}</small></button>)}</div></section>
          <section className="inspector-card"><h3>SPATIAL METRICS <span>DEMO DATA</span></h3><div className="inspector-stats"><div><small>LAT RANGE</small><b>23.8206° → 23.8241°S</b></div><div><small>LON RANGE</small><b>68.2396° → 68.2348°W</b></div><div><small>PIXEL FOOTPRINT</small><b>{region.area} · SAMPLE</b></div><div><small>FRAME DELTA</small><b>+7.2% · SAMPLE</b></div></div></section>
          <section className="inspector-card spectrum-card"><h3>SPECTRAL SHIFT <span>SAMPLE ONLY</span></h3><svg viewBox="0 0 260 56" role="img" aria-label="Illustrative spectral shift chart"><path d="M3 12 C42 18 58 40 91 33 S142 10 174 21 S218 44 257 38"/><path className="spectral-secondary" d="M3 28 C43 14 66 17 94 24 S139 46 175 29 S225 18 257 24"/><circle cx="92" cy="33" r="3"/><circle cx="175" cy="29" r="3"/></svg><div className="band-legend"><span>B02 <b>0.49μm</b></span><span>B08A <b>0.86μm</b></span><span>SWIR-2 <b>2.20μm</b></span></div><p>Spectral values are illustrative only; the local upload path compares RGB image pixels.</p></section>
          <section className="inspector-card observation-card"><h3>LOCAL CV OBSERVATIONS</h3><p><b>Thresholded pixel change:</b> Candidate regions are based on local RGB difference, not a trained event classifier.</p><p><b>Cause assessment:</b> Natural versus human-made activity remains unresolved.</p></section>
        </>}
        <div className="inspector-actions"><button className="button button-primary" onClick={onRun} disabled={busy}>{busy ? 'Analyzing…' : previews ? 'Run Local Comparison' : 'Add Images to Analyze'}</button><button className="button button-secondary" onClick={onUpload}><Glyph>＋</Glyph> Choose Image Pair</button><button className="button button-secondary" onClick={onExport}><Glyph>⇩</Glyph> Export JSON</button><button className="button button-secondary" onClick={() => setNotice('Geospatial export is unavailable until image registration is implemented.')}><Glyph>⌖</Glyph> Geospatial Export <small>Unavailable</small></button></div>
        {notice && <p className="inspector-notice" role="status">{notice}</p>}
      </aside>
    </div>
    {error && <div className="toast error-toast" role="alert">{error}</div>}
  </div>
}

type ReportProps = {
  before: File | null
  after: File | null
  previews: { before: string; after: string } | null
  result: AnalysisResult | null
  onExport: () => void
  onCompare: () => void
  onConfigure: () => void
}

function IntelligenceReport({ before, after, previews, result, onExport, onCompare, onConfigure }: ReportProps) {
  const [reviewed, setReviewed] = useState(false)
  const generated = result ? result.report.analysis_timestamp : 'NOT GENERATED'
  const isSample = !result && !previews

  return <div className="report-page">
    <div className="report-security"><span><i className="dot dot-lime" /> {result ? 'LOCAL CV RESULT' : previews ? 'INPUT PAIR · ANALYSIS PENDING' : 'REFERENCE SAMPLE'}</span><span>{result || previews ? 'AI INFERENCE NOT CONFIGURED' : 'ILLUSTRATIVE CONTENT · NOT A GENERATED REPORT'}</span><span className="report-integrity">● LOCAL WORKSTATION</span></div>
    <div className="report-breadcrumb">Analysis History <i>/</i> {result ? result.analysis_id.toUpperCase() : previews ? 'CUSTOM-IMAGE-PAIR' : 'ATACAMA-SALAR-094'} <i>/</i> <b>Intelligence Report</b></div>
    <header className="report-titlebar"><div><span className="section-label">IMAGE CHANGE DOSSIER · {result ? 'RETAINED ANALYSIS' : previews ? 'ANALYSIS PENDING' : 'SAMPLE TEMPLATE'}</span><h1>{result ? `IR-${result.analysis_id.slice(0, 12).toUpperCase()}` : previews ? 'DRAFT-UNANALYZED' : 'DRAFT-SALAR-094'}</h1><div className="report-meta"><span>GENERATED (UTC): {generated}</span><span>AOI: {result?.location || 'Not provided'}</span></div></div><div className="report-actions"><button className="button button-secondary" onClick={onCompare}><Glyph>◫</Glyph> View Comparison</button><button className="button button-secondary" onClick={() => window.print()}><Glyph>▧</Glyph> Print Report</button>{result && <><a className="button button-secondary" href={`/api/report/${result.analysis_id}/download?format=markdown`}>Markdown</a><a className="button button-secondary" href={`/api/report/${result.analysis_id}/download?format=html`}>HTML</a></>}<button className="button button-primary" onClick={onExport}><Glyph>⇩</Glyph> Export JSON</button></div></header>

      <div className="epistemic-callout"><Glyph>ⓘ</Glyph><span>{result ? result.report.classification_explanation : previews ? 'INPUTS SELECTED, BUT NOT ANALYZED. Run the local comparison to generate measured metrics.' : 'REFERENCE ONLY: sample claims are illustrative and not analysis results.'}</span></div>

    {result && <section className="panel report-comparison"><header className="panel-header"><h2><Glyph>▤</Glyph> Generated Report Findings</h2><span className="chip">{result.report.classification_source.replaceAll('_', ' ')}</span></header><div className="report-card-body"><p><b>Category:</b> {result.report.change_category.replaceAll('_', ' ')} · <b>Heuristic visual extent:</b> {result.report.severity.replaceAll('_', ' ')}</p><p>{result.report.severity_explanation}</p><h3>Detected regions and bounding boxes</h3>{result.regions.length ? <div className="report-region-list">{result.regions.map(region => <p key={region.region_id}><b>{region.region_id}</b> · ({region.x}, {region.y}, {region.width}, {region.height}) · {region.area.toLocaleString()} px · {region.percent_of_valid_area.toFixed(3)}% of valid area</p>)}</div> : <p>No regions passed the configured threshold.</p>}<div className="report-analysis-grid"><div><h3>Alternatives</h3><ul>{result.report.alternative_explanations.map((item, i) => <li key={`alt-${i}`}>{item}</li>)}</ul><h3>Limitations and uncertainty</h3><ul>{result.report.limitations.map((item, i) => <li key={`limit-${i}`}>{item}</li>)}</ul></div><div><h3>Recommended verification steps</h3><ol>{result.report.recommended_verification_steps.map((item, i) => <li key={`verify-${i}`}>{item}</li>)}</ol></div></div><p className="inspector-disclaimer">Confidence: {result.report.confidence == null ? `Not available. ${result.report.confidence_explanation}` : result.report.confidence}</p></div>{result.annotated_preview && <div className="evidence-triptych"><figure className="evidence-frame"><div className="evidence-frame-head"><b>ANNOTATED COMPARISON</b></div><img src={result.annotated_preview} alt="Backend-generated annotated image with detected regions" /></figure><figure className="evidence-frame"><div className="evidence-frame-head"><b>DIFFERENCE MAP</b></div><img src={result.difference_preview} alt="Backend-generated difference-map preview" /></figure></div>}</section>}

    <section className="report-comparison panel"><header className="panel-header"><h2><Glyph>▧</Glyph> Image Evidence &amp; CV Summary</h2><span className="chip">{result || previews ? 'UPLOADED IMAGE PAIR' : 'REFERENCE SAMPLE'}</span><span className="report-panel-meta">{previews ? 'RGB INPUTS · NO GEOLOCATION' : 'SAMPLE SENSOR METADATA · UNVERIFIED'}</span></header><div className="evidence-triptych">
      <article className="evidence-frame"><div className="evidence-frame-head"><b>PANEL A · T0 BASELINE</b><span>{previews ? before?.name : 'SAMPLE · SENTINEL-2C'}</span></div><img src={previews ? previews.before : '/samples/report-before.png'} alt={previews ? 'Baseline image for report' : 'Illustrative baseline satellite scene'} /><div className="evidence-caption">{previews ? 'Uploaded baseline · RGB preview' : 'Illustrative reference image · not an analyzed input'}</div></article>
      <article className="evidence-frame"><div className="evidence-frame-head"><b>PANEL B · T1 LATEST</b><span>{previews ? after?.name : 'SAMPLE · WORLDVIEW-3'}</span></div><img src={previews ? previews.after : '/samples/report-after.png'} alt={previews ? 'Latest image for report' : 'Illustrative latest satellite scene'} /><div className="evidence-caption">{previews ? 'Uploaded latest image · RGB preview' : 'Illustrative reference image · not an analyzed input'}</div></article>
      <article className="evidence-frame delta-frame"><div className="evidence-frame-head"><b>PANEL C · PIXEL DELTA</b><span>{result ? 'LOCAL CV METRICS' : isSample ? 'SAMPLE ONLY' : 'ANALYSIS PENDING'}</span></div><div className="delta-summary"><div className="delta-glyph">Δ</div><b>{result ? `${result.changed_percent.toFixed(2)}%` : isSample ? '+14.82%' : '—'}</b><span>{result ? 'pixels above fixed threshold' : isSample ? 'illustrative change value' : 'run comparison to calculate'}</span><div className="delta-track"><i style={{ width: `${result ? Math.min(result.changed_percent, 100) : isSample ? 62 : 0}%` }} /></div><small>{result ? `${result.changed_regions} connected candidate regions` : isSample ? 'No CV analysis has been run' : 'Analysis pending'}</small></div><div className="evidence-caption">{result ? 'No spatial mask returned by the current API' : isSample ? 'Reference figure · not a generated mask' : 'Mask preview not available from current API'}</div></article>
    </div><div className="comparison-metadata"><span>T0: {previews ? before?.name : '2024-04-12 · sample timestamp'}</span><span>T1: {previews ? after?.name : '2024-10-28 · sample timestamp'}</span><span>CO-REGISTRATION: {result ? 'DIMENSION RESIZE ONLY' : previews ? 'NOT PERFORMED' : 'SAMPLE VALUE NOT VERIFIED'}</span><span>BANDING: {previews ? 'RGB FILES' : 'SAMPLE METADATA ONLY'}</span></div></section>

    <section className="report-analysis-grid">
      <article className="panel report-facts"><header className="panel-header"><h2><Glyph>⌕</Glyph> Computer Vision Observations</h2><span className="chip chip-lime">DETERMINISTIC METRICS</span></header><div className="report-card-body">{result ? <><div className="fact-row"><span className="fact-id">OBSERVED CV FACT 01</span><b>Changed pixels</b><p>{result.changed_pixels.toLocaleString()} of {result.total_pixels.toLocaleString()} pixels exceeded the backend's fixed grayscale difference threshold.</p><small>METHOD: ABSOLUTE DIFFERENCE · THRESHOLD 30/255</small></div><div className="fact-row"><span className="fact-id">OBSERVED CV FACT 02</span><b>Connected candidate regions</b><p>{result.changed_regions} connected components met the minimum 16-pixel area filter.</p><small>GEOGRAPHIC EXTENT: NOT AVAILABLE</small></div><div className="fact-row"><span className="fact-id">PROCESSING NOTE</span><b>Dimension handling</b><p>The latest image is resized to the baseline dimensions when the pair does not match.</p><small>GEOREFERENCED ALIGNMENT: NOT PERFORMED</small></div></> : previews ? <><div className="fact-row"><span className="fact-id">INPUT STATUS</span><b>Two images selected</b><p>{before?.name} and {after?.name} are ready for the local comparison.</p><small>ANALYSIS: NOT RUN</small></div><div className="fact-row"><span className="fact-id">AVAILABLE METHOD</span><b>Local OpenCV comparison</b><p>Run the image comparison to measure thresholded pixel change and connected candidate regions.</p><small>NO EXTERNAL MODEL REQUIRED</small></div><div className="fact-row"><span className="fact-id">SPATIAL METRICS</span><b>Not available for this pair</b><p>Geographic area, pixel footprint in km², and georeferenced alignment are not produced.</p><small>LOCATION METADATA: UNAVAILABLE</small></div></> : <><div className="fact-row sample-fact"><span className="fact-id">SAMPLE CLAIM · NOT VERIFIED</span><b>Reported surface change: +14.82%</b><p>This figure is copied from the visual reference only. No uploaded image pair has been analyzed in this session.</p><small>LOCAL ANALYSIS STATUS: AWAITING INPUT</small></div><div className="fact-row sample-fact"><span className="fact-id">SAMPLE CLAIM · NOT VERIFIED</span><b>Reported brine expansion: 2.41 km²</b><p>OrbitalPulse cannot calculate physical area without georeferenced imagery and spatial registration.</p><small>GEOSPATIAL AREA: NOT AVAILABLE</small></div><div className="fact-row sample-fact"><span className="fact-id">AVAILABLE METHOD</span><b>Local OpenCV comparison</b><p>Upload two RGB images to measure thresholded pixel change and connected candidate regions.</p><small>NO EXTERNAL MODEL REQUIRED</small></div></>}</div><footer className="report-panel-footer"><span>PIPELINE: OPENCV GRAYSCALE ABSOLUTE DIFFERENCE</span><span>CAUSE CLASSIFICATION: NOT PERFORMED</span></footer></article>

      <article className="panel report-ai"><header className="panel-header"><h2><Glyph>✳</Glyph> Semantic Interpretation</h2><span className={`chip ${result?.semantic_status === 'complete' ? 'chip-lime' : ''}`}>{result ? result.semantic_status.replaceAll('_', ' ').toUpperCase() : 'NOT GENERATED'}</span></header><div className="report-card-body">{result?.semantic_analysis ? <><div className="ai-state"><div className="ai-state-icon">AI</div><div><b>{result.semantic_analysis.category.replaceAll('_', ' ')}</b><p>{result.semantic_analysis.observation}</p><p>Possible explanation: {result.semantic_analysis.possible_event}</p></div></div><div className="hypothesis-list"><span className="section-label">SUPPORTING EVIDENCE</span>{result.semantic_analysis.supporting_evidence.map((item, index) => <div key={`evidence-${index}`}><b>{item}</b><em>OBSERVED</em></div>)}<span className="section-label">ALTERNATIVE EXPLANATIONS</span>{result.report.alternative_explanations.map((item, index) => <div key={`alternative-${index}`}><b>{item}</b><em>UNRESOLVED</em></div>)}</div></> : <div className="ai-state"><div className="ai-state-icon">CV</div><div><b>{result ? 'Semantic interpretation unavailable' : 'No analysis report yet'}</b><p>{result?.semantic_error ?? result?.report.classification_explanation ?? 'Run an analysis to generate a report from the uploaded pair.'}</p><p>{result?.report.classification_explanation}</p></div></div>}<button className="button button-secondary ai-configure" onClick={onConfigure}>Provider configuration details <Glyph>→</Glyph></button></div><footer className="report-panel-footer"><span>CLASSIFICATION SOURCE: {result?.report.classification_source ?? 'NONE'}</span><span>CONFIDENCE: {result?.report.confidence ?? 'NOT AVAILABLE'}</span></footer></article>
    </section>

    <section className="panel recommended-actions"><header className="panel-header"><h2><Glyph>✓</Glyph> Recommended Verification Steps</h2><span className="report-panel-meta">ANALYST CHECKLIST · NOT AN AUTOMATED DIRECTIVE</span></header><div className="verification-grid"><article><span className="action-step">STEP 01 · REQUIRED</span><h3>Confirm image alignment</h3><p>Use the same geographic footprint and validate co-registration before treating pixel changes as physical changes.</p><button onClick={onCompare}>Open image comparison →</button></article><article><span className="action-step">STEP 02 · CONTEXT</span><h3>Review acquisition conditions</h3><p>Check capture dates, illumination, cloud cover, and sensor differences for possible false change signals.</p><button onClick={onCompare}>Review image pair →</button></article><article><span className="action-step">STEP 03 · OPTIONAL</span><h3>Collect independent evidence</h3><p>Use georeferenced multispectral or SAR data and trusted ground context before assigning a cause.</p><button onClick={onConfigure}>View provider settings →</button></article></div></section>

    <footer className="report-signoff"><div><span className="analyst-stamp">OP</span><div><b>OrbitalPulse Analyst Workspace</b><small>LOCAL REPORT · {result ? result.analysis_id : 'SAMPLE TEMPLATE'}</small></div></div><div className="signoff-status"><span><i className={`dot ${reviewed ? 'dot-sage' : 'dot-amber'}`} /> {reviewed ? 'MARKED REVIEWED LOCALLY' : 'DRAFT · AWAITING ANALYST REVIEW'}</span><button className="button button-primary" onClick={() => setReviewed(value => !value)}>{reviewed ? 'Undo review mark' : 'Mark reviewed'}</button></div></footer>
  </div>
}
