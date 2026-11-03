**Tech stack:** Python, Stim, PyMatching, FastAPI, React, TypeScript, Tailwind CSS, Plotly, SQLite, Docker Compose

# QubitGuard

**Quantum Error Correction Simulator & Decoder Benchmarking Platform**

QubitGuard runs noisy quantum-memory experiments with Stim, predicts logical observable flips with PyMatching and simple baselines, and compares recovery accuracy and CPU decoding throughput in a React dashboard. All simulations run locally; experiment history lives in SQLite.

## Run with Docker Compose

Install Docker Desktop (or Docker Engine with Compose), then run from this repository:

```sh
./start.sh
```

The launcher builds both images, starts all services in the background, and waits for startup.

Open **[http://localhost:8766](http://localhost:8766)**. Set `QUBITGUARD_PORT` to use a different local port. The first ARM Linux build may take several minutes because Stim and PyMatching can compile from source. Compilers remain in a separate build stage. No paid APIs, accounts, API keys, GPU or quantum hardware are needed.

```sh
docker compose logs -f backend    # experiment IDs, access logs, failures
docker compose down               # stop; preserve saved experiments
```

SQLite is stored in the named `experiments` volume. Removing that volume removes history. The frontend is bound to loopback and the backend is accessible only within the Compose network.

## Local development

Use **Python 3.11+** and **Node 22+**. The Python lock records the validated environment, while npm uses its package lock.

```sh
python3.11 -m venv .venv311
source .venv311/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
npm --prefix frontend ci
```

Start the backend in one terminal:

```sh
source .venv311/bin/activate
uvicorn qubitguard.api:app --host 127.0.0.1 --port 8765
```

Start the dashboard in another:

```sh
npm --prefix frontend run dev -- --port 5173
```

Open **[http://localhost:5173](http://localhost:5173)**. Vite proxies `/api` to port 8765. Interactive API documentation is at **[http://localhost:8765/docs](http://localhost:8765/docs)**. Local database: `data/qubitguard.sqlite`; override with `QUBITGUARD_DB`. Keep one backend worker. Do not use Uvicorn auto-reload during experiments; server restarts mark interrupted jobs failed.

## Try the main experiment

1. Select repetition code, distances 3 / 5 / 7, physical probabilities 1% / 3% / 5%, five rounds, and 10,000 shots per point.
2. Compare MWPM with majority vote. Run the experiment to sample real data; the dashboard never substitutes illustrative values.
3. Inspect logical error rates and 95% Wilson intervals. Toggle logarithmic scale to see small probabilities. Zero-failure points show an upper confidence bound on the log chart.
4. Select a results row to inspect that cell's decoding time, explore its first 16 syndrome samples, and export JSON or CSV.
5. Increase to 100,000 shots for narrower intervals. Saved experiments can be reopened from history.

Surface-code X and Z memories support MWPM and the no-correction baseline. Their circuit-level noise model differs from repetition's bit-flip model. The interface supports configuring seeds, shots, measurement rounds, distances, noise levels and decoder selection. The API supports odd distances through 15 and p through 0.2, with workload limits; the dashboard offers a practical subset.

## Recorded result

In the checked-in 100,000-shot repetition sweep at **p = 1%**, five rounds and seed 42, MWPM's observed logical failure probability fell from **0.437% (d=3)** to **0.028% (d=5)** to **0.001% (d=7)**. The last estimate is one failure; its 95% Wilson interval is approximately **0.0002%–0.0057%**. This is evidence of distance suppression under the specified model, not a threshold claim.

See [the full result tables](docs/results.md), [repetition raw results](benchmarks/repetition-results.json), and [surface raw results](benchmarks/surface-results.json). Each file includes environment provenance and sampled detection events.

## Reproduce benchmarks and run checks

```sh
qubitguard-benchmark benchmarks/repetition-scaling.json --output data/repetition.json
qubitguard-benchmark benchmarks/surface-scaling.json --output data/surface.json
pytest -q
npm --prefix frontend run build
docker compose config --quiet
```

The same simulation path powers the CLI and API. Decoders receive identical shots within each parameter cell. Root seed, per-cell sampler seed, package versions, platform, batch size and noise model are exported. For exact samples, use the same Stim environment and batching; seeds do not guarantee cross-platform identical samples. CPU timings vary with load.

Tests cover noiseless memories for all code families, exhaustive majority-decoder bit patterns, known single-error recovery, an analytic binomial cross-check, matched-shot reproducibility, validation, persistent API lifecycle and export formats. GitHub Actions runs scientific/API tests, a surface benchmark, the TypeScript production build and container builds.

## Learn and inspect

- [Executed QEC fundamentals notebook](notebooks/01_qec_fundamentals.ipynb): circuits, detector samples, decoder comparisons and an analytic check. Open with Jupyter using the project environment; Jupyter is optional. `python scripts/create_notebook.py` executes and regenerates it.
- [Scientific model and limitations](docs/science.md): Pauli errors, stabilizers, decoder definitions, rates, uncertainty and timing methodology.
- [Architecture and API](docs/architecture.md): local queue, SQLite persistence, failure recovery, observability and endpoint reference.
- [Deltakit extension investigation](docs/deltakit.md): optional local tooling exploration and acceptance criteria. Deltakit is not integrated into the core benchmark or validated dependency lock.

```text
backend/qubitguard/    simulation engine, models, API, storage, CLI
backend/tests/         scientific and API correctness tests
frontend/src/          React dashboard, Plotly charts, syndrome explorer
benchmarks/            reproducible configurations and actual results
notebooks/             executed learning notebook
scripts/               notebook generation
.github/workflows/     CI
```

## Scope and limitations

This is a single-user simulation and benchmarking project. It is not a real-time quantum control system, a production decoder service, or a hardware benchmark. Repetition protects bit flips only. Surface decoding uses graphlike decomposition without correlation-aware matching. The reported rate is per whole memory experiment, not per round. Timing percentiles describe **batch averages**, not single-shot tails. The API queue is bounded and in-memory; interrupted jobs are marked failed rather than resumed. There is no authentication or distributed worker coordination, so keep deployment local.

Primary tools: [Stim](https://github.com/quantumlib/Stim), [PyMatching](https://pymatching.readthedocs.io/en/stable/), [Deltakit](https://github.com/Deltakit/deltakit), FastAPI, React, TypeScript, Tailwind, Plotly and SQLite. MIT license; dependencies retain their own licenses.
