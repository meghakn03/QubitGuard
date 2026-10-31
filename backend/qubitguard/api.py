import csv
import io
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, Response

from .engine import build_circuit, run_experiment
from .models import ExperimentConfig
from .store import Store

logger = logging.getLogger("qubitguard")


def create_app(db_path=None):
    store = Store(db_path or os.getenv("QUBITGUARD_DB", "data/qubitguard.sqlite"))
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="qec")
    slots = threading.BoundedSemaphore(4)

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        yield
        pool.shutdown(wait=True)

    app = FastAPI(title="QubitGuard", version="0.1.0", lifespan=lifespan)
    app.state.store = store

    def execute(key, config):
        try:
            store.update(key, status="running")
            result = run_experiment(config, lambda done, total: store.update(key, progress=round(100 * done / total)))
            store.update(key, status="completed", progress=100, result=result)
            logger.info("experiment_completed id=%s duration_s=%.3f", key, result["provenance"]["elapsed_seconds"])
        except Exception:
            logger.exception("experiment_failed id=%s", key)
            store.update(key, status="failed", error="Simulation failed. Check backend logs for details and retry with a smaller sweep.")
        finally:
            slots.release()

    def get_or_404(key):
        item = store.get(key)
        if item is None:
            raise HTTPException(404, "Experiment not found")
        return item

    @app.get("/api/health")
    def health():
        with store.connect() as db:
            db.execute("SELECT 1")
        return {"status": "ok", "engine": "stim", "version": "0.1.0"}

    @app.post("/api/experiments", status_code=202)
    def create(config: ExperimentConfig):
        if not slots.acquire(blocking=False):
            raise HTTPException(429, "Local queue is full (four experiments); wait for a run to finish")
        try:
            key = store.create(config.model_dump())
            pool.submit(execute, key, config)
        except Exception:
            slots.release()
            raise
        return {"id": key, "status": "queued"}

    @app.get("/api/experiments")
    def history(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
        return store.list(limit, offset)

    @app.get("/api/experiments/{key}")
    def detail(key: str):
        return get_or_404(key)

    @app.get("/api/experiments/{key}/export")
    def export(key: str, format: str = Query("json", pattern="^(json|csv)$")):
        item = get_or_404(key)
        if item["status"] != "completed":
            raise HTTPException(409, "Results are available after the experiment completes")
        if format == "json":
            import json
            return Response(json.dumps(item, indent=2), media_type="application/json",
                headers={"Content-Disposition": f'attachment; filename="qubitguard-{key}.json"'})
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["code", "rounds", "distance", "physical_error_rate", "shots", "seed", "decoder", "failures", "logical_error_rate", "ci_low", "ci_high", "mean_decode_us"])
        for cell in item["result"]["results"]:
            for d in cell["decoders"]:
                writer.writerow([item["config"]["code"], item["config"]["rounds"], cell["distance"], cell["physical_error_rate"], cell["shots"], cell["seed"], d["decoder"], d["failures"], d["logical_error_rate"], *d["confidence_interval"], d["mean_decode_us"]])
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="qubitguard-{key}.csv"'})

    @app.get("/api/experiments/{key}/circuit", response_class=PlainTextResponse)
    def circuit(key: str, distance: int, physical_error_rate: float):
        config = ExperimentConfig(**get_or_404(key)["config"])
        if distance not in config.distances or physical_error_rate not in config.physical_error_rates:
            raise HTTPException(422, "Select a distance and noise rate from this experiment")
        return str(build_circuit(config.code, distance, config.rounds, physical_error_rate))

    return app


app = create_app()
