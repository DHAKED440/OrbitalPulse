# OrbitalPulse

OrbitalPulse is a hackathon-scale satellite and aerial imagery change-detection foundation. It compares two images locally with OpenCV and produces a basic explainable report without requiring an external AI service. Optional vision analysis is isolated behind a provider interface for later integration.

## Repository architecture

- `frontend/`: React, TypeScript, Vite, Tailwind CSS interface and typed API client.
- `backend/`: FastAPI routes, Pydantic schemas, configuration, local storage, and modular CV/vision services.
- `backend/data/`: runtime upload and result directories (ignored by Git).
- `data/samples/`: place non-sensitive sample imagery here.
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

Set optional provider values in `.env` only if you later implement and enable a compatible vision provider. No API key is needed for local change detection.

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

- `GET /api/health`: service status and active vision provider.
- `POST /api/analyze`: multipart upload with `before_image` and `after_image`; validates size and image decoding, stores files locally, computes a thresholded difference map and summary, and returns an explainable result.

The first CV implementation aligns images to the first image's dimensions using area interpolation, computes grayscale absolute difference, and thresholds changed pixels. Treat the result as a prototype signal: it is not geospatially registered and does not classify causes as natural or human-made. AI provider calls are deliberately not required by this path.

## Checks

```powershell
npm run build
backend/.venv/Scripts/python -m pytest backend/tests
```

## Next implementation steps

1. Add geospatial registration and robust scene normalization before comparing satellite acquisitions.
2. Add annotated result visualization and downloadable reports.
3. Implement a real provider adapter with timeouts, structured output validation, and provider-specific environment settings.
4. Add fixtures and tests for corrupt images, upload limits, dimension mismatches, and CV thresholds.
5. Evaluate the pipeline on representative imagery and clearly label uncertainty and false positives.
