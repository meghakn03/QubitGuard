# Validation record

Validated locally on 1 November 2026:

- 20 pytest scientific, validation, queue and API tests passed on Python 3.11.
- The learning notebook was executed and saved with its outputs.
- TypeScript compilation and Vite production build passed. Plotly produces a large-bundle advisory; it does not prevent the build.
- Both Docker images built on ARM Linux. Stim and PyMatching compiled in the compiler stage; the runtime runs as a non-root user.
- Docker Compose started successfully; backend health passed.
- `scripts/smoke_compose.py` passed through Nginx: dashboard HTML, health, experiment submission, simulation completion, SQLite retrieval, JSON and CSV exports.
- The Docker-served dashboard ran the default nine-point, 90,000-shot distance sweep to completion. Browser checks covered charts, log scaling, history, reproducibility metadata and syndrome inspection. The narrow-screen chart legend was checked visually.
- Temporary development servers were stopped; the Compose app was left running on local port 8766.

GitHub Actions workflows are configured but were not run remotely in this session. Deltakit remains a documented optional extension and was not installed or tested. A dependency deprecation warning from Starlette's HTTPX test-client adapter is present; all tests pass.
