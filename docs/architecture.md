# Architecture notes

The browser handles selection and presentation. The FastAPI service validates uploads, stores them in temporary local storage, and delegates pixel comparison to an OpenCV service. A separate vision provider interface allows later AI descriptions without making the core path depend on network access or credentials.

The current comparison is intentionally a baseline. It uses grayscale absolute difference and a fixed threshold, and resizes mismatched inputs to the baseline dimensions. It does not perform geospatial registration, account for lighting or seasonal changes, generate a spatial overlay, or infer event cause. Keep reports explicit about those limits.

Uploads are limited per file, accepted MIME types are checked, and Pillow verifies decoded file format before OpenCV processing. For deployment beyond a local demo, add request-level body limits, retention/cleanup, resource limits, authentication, and more robust image normalization.
