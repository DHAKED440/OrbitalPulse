# OrbitalPulse

OrbitalPulse is a hackathon-scale satellite and aerial imagery change-detection foundation. It compares two images locally with OpenCV and produces a basic explainable report without requiring an external AI service. Optional vision analysis is isolated behind a provider interface for later integration.

## Repository architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS interface and typed API client.
- `backend/`: FastAPI routes, Pydantic schemas, configuration, local storage, and modular CV/vision services.
- `backend/data/`: runtime upload and result directories (ignored by Git).
- `data/samples/`: labeled, generated synthetic scenario pairs and metadata (not satellite observations).
- `docs/`: architecture and implementation notes.

There was no pre-existing application or dependency manifest in the repository; this foundation uses the requested stack.

## Requirements

- Node.js 20+ and npm
- Python 3.11+

## Setup

From the repository root:

```powershell
Copy-Item .env.example .env
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
npm install
```

Set `VITE_API_BASE_URL` to the backend origin when the browser should call it directly (for example `http://127.0.0.1:8000`). Leave it empty to use the Vite `/api` proxy. `VITE_MAX_UPLOAD_MB` configures the browser-side size limit; keep it aligned with `MAX_UPLOAD_MB` on the backend. Set optional provider values only if a compatible vision provider is enabled. No API key is needed for local change detection.

## Run

From the repository root, start the API in one terminal:

```powershell
backend/.venv/Scripts/Activate.ps1
uvicorn app.main:app --reload --app-dir backend
```

From the repository root, start the frontend in a second terminal:

```powershell
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend proxies `/api` requests to `http://127.0.0.1:8000`. API docs are at `http://127.0.0.1:8000/docs`.

The complete first-time PowerShell setup and run sequence is:

```powershell
Copy-Item .env.example .env
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
npm install
# Terminal 1 (repository root):
uvicorn app.main:app --reload --app-dir backend
# Terminal 2 (repository root):
npm run dev
```

In the New Analysis dialog choose both T0 and T1 images (or assign backend samples), optionally enter location/date metadata, then select **Analyze Changes**. The comparison view displays backend pixel metrics and the saved annotated image; selecting a returned region highlights its bounding box. Open Intelligence Report to retrieve and show the persisted report. AI inference is optional and local CV results remain available if the provider is disabled or fails.

## Hackathon demo sequence

Three reproducible **synthetic** image pairs are shipped under `data/samples/`: vegetation loss, new construction/land disturbance, and flood-like water expansion. They are computer-generated illustrations, not real satellite observations. Pair details and intended visual signals are in each folder's `scenario.json`. Regenerate them deterministically with:

```powershell
python scripts/generate_demo_samples.py
```

Recommended live sequence:

1. Open **New Analysis → Choose Image Pair** and select **Load image pair** for **Vegetation loss**. The T0 and T1 file slots populate together and remain editable.
2. Select **Analyze Changes**. The backend computes the normal OpenCV comparison; the UI has no preset metrics for any scenario.
3. Use **Dual-Swipe** for before/after, then **Diff Heatmap** for the backend red pixel-difference overlay and **Vector Overlay** for backend candidate boxes. Click a detected region to highlight its pixel bounding box.
4. Review the changed-pixel percentage, pixel count, image dimensions, and connected-region count returned by the API. Expect a broad clearing signal for vegetation loss, new pad/building/road signals for construction, and a large water-expansion signal for the flood-like pair. Exact metrics are generated at run time and may vary with CV/library versions.
5. Open **Intelligence Report**. With `VISION_PROVIDER=disabled`, the report clearly marks AI as unavailable and presents the measured CV evidence as an analyst-review fallback. It also explains that this prototype does not georegister inputs or determine whether a cause is natural or human-made.
6. Repeat for construction and flood-like expansion. The picker metadata identifies each pair as synthetic and summarizes the expected visible change.

Backend sample discovery reads paired `before.png`/`after.png` files next to each valid `scenario.json` under `data/samples/`. Add future demos as new subfolders with this same layout and metadata; the UI always uses analysis results returned from the API.

## API

- `GET /api/health`: service status and active vision provider.
- `GET /api/samples` and `GET /api/samples/{filename}`: list and retrieve images from `data/samples/`.
- `POST /api/analyze`: multipart upload with `before_image`, `after_image`, and optional `location`, `before_date`, and `after_date`; validates size and image decoding, performs local CV, and returns measured metrics, pixel-coordinate regions, and annotated-image/report URLs.
- `GET /api/reports/{analysis_id}` and `GET /api/reports/{analysis_id}/annotated`: retrieve a persisted analysis report and its annotated PNG from local temporary storage.

The first CV implementation aligns images to the first image's dimensions using area interpolation, computes grayscale absolute difference, and thresholds changed pixels. Treat the result as a prototype signal: it is not geospatially registered and does not classify causes as natural or human-made. AI provider calls are deliberately not required by this path.

## Checks

```powershell
npm run build
backend/.venv/Scripts/python -m pytest backend/tests
```

## Next implementation steps

1. Add geospatial registration and robust scene normalization before comparing satellite acquisitions.
2. Add georeferenced raster support and physical area estimates.
3. Implement a real provider adapter with timeouts, structured output validation, and provider-specific environment settings.
4. Expand route tests for malformed files, upload limits, and provider failures.
5. Evaluate the pipeline on representative imagery and clearly label uncertainty and false positives.
