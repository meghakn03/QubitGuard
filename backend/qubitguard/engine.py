"""Stim sampling and matched-shot decoder evaluation. No synthetic dashboard data."""
import hashlib
import importlib.metadata
import platform
import time
from math import sqrt
from typing import Callable, Optional

import numpy as np
import pymatching
import stim

from .models import ExperimentConfig

BATCH_SIZE = 4096
ENGINE_VERSION = "1"


def build_circuit(code: str, distance: int, rounds: int, p: float) -> stim.Circuit:
    if code != "repetition":
        task = {"surface_x": "surface_code:rotated_memory_x", "surface_z": "surface_code:rotated_memory_z"}[code]
        return stim.Circuit.generated(task, distance=distance, rounds=rounds,
            after_clifford_depolarization=p, before_round_data_depolarization=p,
            before_measure_flip_probability=p, after_reset_flip_probability=p)
    # Phenomenological bit-flip memory: noisy data and check readout,
    # ideal preparation, parity gates, and final data readout.
    circuit = stim.Circuit()
    ancillas = list(range(distance, 2 * distance - 1))
    circuit.append("R", range(2 * distance - 1))
    for t in range(rounds):
        circuit.append("X_ERROR", range(distance), p)
        for i, anc in enumerate(ancillas):
            circuit.append("CX", [i, anc, i + 1, anc])
        circuit.append("X_ERROR", ancillas, p)
        circuit.append("MR", ancillas)
        for i in range(distance - 1):
            targets = [stim.target_rec(i - (distance - 1))]
            if t:
                targets.append(stim.target_rec(i - 2 * (distance - 1)))
            circuit.append("DETECTOR", targets, [i + 0.5, 0, t])
        circuit.append("TICK")
    circuit.append("M", range(distance))
    for i in range(distance - 1):
        circuit.append("DETECTOR", [stim.target_rec(i - distance), stim.target_rec(i + 1 - distance),
            stim.target_rec(i - distance - (distance - 1))], [i + 0.5, 0, rounds])
    circuit.append("OBSERVABLE_INCLUDE", [stim.target_rec(-1)], 0)
    return circuit


def majority_decode(syndromes: np.ndarray, distance: int, rounds: int) -> np.ndarray:
    # Temporal XOR telescopes to the perfect final adjacent-data parities.
    parity = np.bitwise_xor.reduce(syndromes.reshape(-1, rounds + 1, distance - 1), axis=1)
    relative = np.zeros((len(syndromes), distance), dtype=np.uint8)
    relative[:, 1:] = np.bitwise_xor.accumulate(parity, axis=1)
    complement = relative.sum(axis=1) > distance // 2
    return (relative[:, -1] ^ complement.astype(np.uint8))[:, None]


def wilson(failures: int, shots: int) -> list[float]:
    z = 1.959963984540054
    rate = failures / shots
    denom = 1 + z * z / shots
    centre = (rate + z * z / (2 * shots)) / denom
    radius = z * sqrt(rate * (1 - rate) / shots + z * z / (4 * shots * shots)) / denom
    return [max(0.0, centre - radius), min(1.0, centre + radius)]


def cell_seed(config: ExperimentConfig, distance: int, p: float) -> int:
    key = f"{ENGINE_VERSION}:{config.seed}:{config.code}:{distance}:{config.rounds}:{p:.17g}"
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little")


def run_experiment(config: ExperimentConfig, progress: Optional[Callable] = None) -> dict:
    started = time.perf_counter()
    results = []
    total = len(config.distances) * len(config.physical_error_rates)
    for distance in config.distances:
        for p in config.physical_error_rates:
            circuit = build_circuit(config.code, distance, config.rounds, p)
            seed = cell_seed(config, distance, p)
            sampler = circuit.compile_detector_sampler(seed=seed)
            setup_started = time.perf_counter()
            matching = pymatching.Matching.from_detector_error_model(circuit.detector_error_model(decompose_errors=True)) if "mwpm" in config.decoders else None
            setup_ms = (time.perf_counter() - setup_started) * 1000
            decode = {
                "mwpm": lambda s: matching.decode_batch(s),
                "majority": lambda s: majority_decode(s, distance, config.rounds),
                "identity": lambda s: np.zeros((len(s), 1), dtype=np.uint8),
            }
            # Warm-up on a separate noiseless array; sampling stream is untouched.
            for decoder in config.decoders:
                decode[decoder](np.zeros((1, circuit.num_detectors), dtype=np.uint8))
            failures = {d: 0 for d in config.decoders}
            timings = {d: [] for d in config.decoders}
            samples = []
            sampling_s = 0.0
            for offset in range(0, config.shots, BATCH_SIZE):
                count = min(BATCH_SIZE, config.shots - offset)
                t = time.perf_counter()
                syndromes, actual = sampler.sample(count, separate_observables=True)
                sampling_s += time.perf_counter() - t
                predictions = {}
                # Rotate decoder order across batches to reduce systematic ordering bias.
                order = config.decoders[offset // BATCH_SIZE % len(config.decoders):] + config.decoders[:offset // BATCH_SIZE % len(config.decoders)]
                for decoder in order:
                    t = time.perf_counter_ns()
                    predicted = decode[decoder](syndromes)
                    elapsed = time.perf_counter_ns() - t
                    timings[decoder].append((elapsed, count))
                    failures[decoder] += int(np.count_nonzero(np.any(predicted != actual, axis=1)))
                    predictions[decoder] = predicted
                if offset == 0:
                    for i in range(min(16, count)):
                        samples.append({"shot": i, "events": np.flatnonzero(syndromes[i]).tolist(),
                            "actual": int(actual[i, 0]), "predictions": {d: int(predictions[d][i, 0]) for d in config.decoders}})
            results.append({"distance": distance, "physical_error_rate": p, "seed": seed,
                "shots": config.shots, "detectors": circuit.num_detectors,
                "coordinates": {str(k): v for k, v in circuit.get_detector_coordinates().items()},
                "sampling_ms": sampling_s * 1000, "matching_setup_ms": setup_ms,
                "samples": samples,
                "decoders": [{"decoder": d, "failures": failures[d],
                    "logical_error_rate": failures[d] / config.shots,
                    "confidence_interval": wilson(failures[d], config.shots),
                    "mean_decode_us": sum(n for n, _ in timings[d]) / config.shots / 1000,
                    "batch_mean_p50_us": float(np.median([n / s / 1000 for n, s in timings[d]])),
                    "batch_mean_p95_us": float(np.percentile([n / s / 1000 for n, s in timings[d]], 95)),
                    "batches": len(timings[d])} for d in config.decoders]})
            if progress:
                progress(len(results), total)
    return {"config": config.model_dump(), "results": results,
        "provenance": {"engine_version": ENGINE_VERSION, "batch_size": BATCH_SIZE,
            "python": platform.python_version(), "platform": platform.platform(),
            "versions": {p: importlib.metadata.version(p) for p in ["stim", "pymatching", "numpy"]},
            "elapsed_seconds": time.perf_counter() - started,
            "noise_model": "phenomenological X data/readout noise; ideal final readout" if config.code == "repetition" else "Stim circuit-level depolarization, data idle, reset and readout noise",
            "rate_definition": "Logical failure probability per complete memory experiment",
            "timing_definition": "Warmed batch decoding only; microseconds per shot; excludes graph setup and sampling"}}
