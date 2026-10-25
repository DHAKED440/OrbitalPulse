# OrbitalPulse

OrbitalPulse is a hackathon-scale satellite and aerial imagery change-detection foundation. It compares two images locally with OpenCV and produces an explainable report without requiring an external AI service. Optional semantic interpretation is isolated behind a configurable provider interface.

## Repository architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS interface and typed API client.
- `backend/`: FastAPI routes, Pydantic schemas, configuration, local storage, and modular CV/vision services.
- `backend/data/`: runtime upload and result directories (ignored by Git).
- `data/samples/`: place non-sensitive sample imagery here.
- `docs/`: architecture and implementation notes.

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

Local computer-vision analysis needs no API key. Optional semantic interpretation uses the OpenAI Responses API and stays disabled by default. To enable it, set `VISION_PROVIDER=openai`, `VISION_API_KEY` to a backend-only API key, and `VISION_MODEL` to a vision-capable model that supports strict JSON Schema output. Set the timeout and image/payload limits with `VISION_REQUEST_TIMEOUT_SECONDS`, `VISION_MAX_IMAGE_DIMENSION`, `VISION_MAX_IMAGE_BYTES`, `VISION_MAX_PAYLOAD_BYTES`, and `VISION_MAX_REGION_CROPS`. Never put the key in frontend configuration.

## Run

Start the API in one terminal:

```powershell
backend/.venv/Scripts/Activate.ps1
uvicorn app.main:app --reload --app-dir backend
```

Start the frontend in another terminal:

```powershell
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend proxies `/api` requests to `http://127.0.0.1:8000`. API docs are at `http://127.0.0.1:8000/docs`.

## API

- `GET /api/health`: backend status plus whether a usable AI provider is available. The current placeholder provider is unavailable; credentials are never returned.
- `POST /api/analyze`: multipart upload with required `before_image` and `after_image`; optional `location`, `before_acquisition_date`, `after_acquisition_date`, `comparison_mode` (`registered` by default, or `original` to skip registration and appearance normalization), and `ai_consent` (defaults to false). Dates use `YYYY-MM-DD`.
- `GET /api/samples`: lists complete before/after pairs found in `data/samples/` (`<scenario>_before.<ext>` and `<scenario>_after.<ext>`). Returns an empty list until sample pairs are added.
- `GET /api/report/{analysis_id}`: retrieves the validated analysis and intelligence report for 24 hours by default; expired or unknown IDs return `404`.
- `GET /api/report/{analysis_id}/download?format=json|markdown|html`: downloads the same retained report (JSON by default), including metrics, regions, evidence previews, classification details, caveats, and verification steps. Unknown or expired IDs return `404`.

The CV service aligns compatible working copies with ORB feature matches and a RANSAC homography. It rejects singular, poorly supported, implausible, and low-overlap transformations before warping. If registration cannot be trusted, it compares resized images without registration and reports a warning. Registered mode performs robust percentile brightness/contrast matching, CLAHE normalization, local SSIM, intensity and edge comparisons, morphology, and connected-component filtering. Region filters are configured with `CHANGE_THRESHOLD`, `MIN_REGION_AREA`, and `MIN_REGION_PERCENT`. The response includes region IDs, boxes, pixel areas, valid-area percentages, relative size categories (small <0.1%, medium 0.1–1%, large ≥1%), edge/texture/color difference indicators, and annotated/difference previews. These indicators describe image evidence only; they do not identify real-world event types. Region coordinates and pixel areas use the before-image pixel grid; no geospatial area is inferred.

The output is a first-pass image comparison, not a validated satellite-event detector. Clouds and haze can obscure the ground and generate broad differences; seasonal vegetation, water levels, agricultural cycles, shadows, and sun-angle changes can resemble events. Different sensors, spectral bands, resolutions, orthorectification, or substantial misalignment can also produce false positives or missed changes. Registration fallback explicitly warns that geometric alignment was not applied. Use `comparison_mode=original` to inspect unregistered, unnormalized appearance as supporting evidence.

### Optional semantic interpretation and image transfer

When `VISION_PROVIDER=openai` is configured, the browser checkbox requires the user to consent for each analysis before the backend sends the two downscaled images and up to `VISION_MAX_REGION_CROPS` before/after region crops to OpenAI for semantic interpretation. The transfer occurs only when both configuration and `ai_consent=true` are present. Without consent, the provider is not called and the local CV report is returned with `semantic_status=consent_required`. Provider outages, rate limits, timeouts, and malformed output likewise do not discard CV results; see `semantic_status` and `semantic_error` in the response. The backend uses the OpenAI Responses API with `store:false`, bounded payloads and a timeout. Review OpenAI's current [image input](https://developers.openai.com/api/docs/guides/images-vision?api-mode=responses) and [structured output](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses) requirements when selecting a model. Configure account and data handling according to your organization’s requirements.

The semantic response separates visible observation, possible explanation, evidence, alternatives, unknowns, and limitations. Categories and indicators are model interpretations, not verified ground truth; they do not establish illegality, intent, or responsibility. The API key remains backend-only. Semantic statuses are `not_requested`, `consent_required`, `unavailable`, `complete`, `failed`, and `rate_limited`.

### Intelligence report rules

Every new analysis includes a UTC timestamp, category, classification source, visual-evidence references, region IDs/boxes and pixel areas, alternatives, limitations, and recommended verification steps. AI classifications retain the model's category but do not receive a fabricated confidence score; current provider responses do not supply calibrated confidence. If semantic interpretation was unavailable, the category is `UNCERTAIN`, the source is `COMPUTER_VISION_HEURISTIC`, and narrative fields are limited to measured CV output plus explicit uncertainty.

Severity is deliberately labeled **heuristic visual extent**, separate from event classification. Rules use changed percentage of valid comparison pixels and the largest region's percentage of that area: low when both are under 0.1%; high when changed area is at least 1% or the largest region is at least 0.5%; otherwise moderate. These rules describe image extent only. A large difference does not imply a severe disaster. HTML downloads escape user/model text; evidence images are embedded from the generated previews.

Uploads are streamed to per-request temporary directories, limited by `MAX_UPLOAD_MB`, `MAX_IMAGE_DIMENSION`, and `MAX_IMAGE_PIXELS`, and removed after processing. `MAX_WORKING_DIMENSION` bounds CV memory use; `CHANGE_THRESHOLD` and `MIN_REGION_AREA` control mask sensitivity and region filtering. Reports are atomically written under server-generated IDs and expire after `REPORT_RETENTION_HOURS`. CORS defaults to the local Vite origins `http://localhost:5173` and `http://127.0.0.1:5173`; set `CORS_ORIGINS` to a comma-separated list to add frontend origins.

Common errors include `400` for corrupt or over-dimensioned images, `413` for oversized files, `415` for unsupported declared media types, `422` for missing uploads or malformed metadata, and `404` for unavailable reports.

## Checks

```powershell
npm run build
backend/.venv/Scripts/python -m pytest backend/tests
```

## Next implementation steps

1. Add geospatial registration and robust scene normalization before comparing satellite acquisitions.
2. Evaluate report severity thresholds against user-reviewed imagery.
3. Evaluate the semantic and CV pipelines on representative imagery and clearly label uncertainty and false positives.
