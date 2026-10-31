from itertools import product
from math import comb

import numpy as np
import pytest
import stim

from qubitguard.engine import build_circuit, majority_decode, run_experiment, wilson
from qubitguard.models import ExperimentConfig


@pytest.mark.parametrize("code", ["repetition", "surface_x", "surface_z"])
def test_noiseless_memory(code):
    cfg = ExperimentConfig(code=code, distances=[3, 5], physical_error_rates=[0], shots=100,
        decoders=["mwpm", "majority"] if code == "repetition" else ["mwpm", "identity"])
    result = run_experiment(cfg)
    assert all(d["failures"] == 0 for cell in result["results"] for d in cell["decoders"])
    assert all(not shot["events"] for cell in result["results"] for shot in cell["samples"])


@pytest.mark.parametrize("distance", [3, 5, 7])
def test_majority_all_bit_patterns(distance):
    patterns = np.array(list(product([0, 1], repeat=distance)), dtype=np.uint8)
    parity = patterns[:, :-1] ^ patterns[:, 1:]
    predicted = majority_decode(parity, distance, 0)[:, 0]
    # Recovery succeeds precisely for patterns with at most floor(d/2) flips.
    success = predicted == patterns[:, -1]
    assert np.array_equal(success, patterns.sum(axis=1) <= distance // 2)


def test_single_data_errors_recover_with_both_decoders():
    import pymatching
    base = build_circuit("repetition", 5, 3, 0.02)
    matching = pymatching.Matching.from_detector_error_model(base.detector_error_model(decompose_errors=True))
    for qubit in range(5):
        circuit = build_circuit("repetition", 5, 3, 0)
        circuit = circuit[:1] + stim.Circuit(f"X_ERROR(1) {qubit}") + circuit[1:]
        syn, actual = circuit.compile_detector_sampler(seed=1).sample(10, separate_observables=True)
        assert np.array_equal(matching.decode_batch(syn), actual)
        assert np.array_equal(majority_decode(syn, 5, 3), actual)


def test_majority_matches_analytic_memory_failure():
    # Each qubit has odd error parity with q=(1-(1-2p)^r)/2.
    d, p, rounds, shots = 3, 0.05, 3, 100000
    cfg = ExperimentConfig(distances=[d], physical_error_rates=[p], rounds=rounds, shots=shots, decoders=["majority"])
    measured = run_experiment(cfg)["results"][0]["decoders"][0]["logical_error_rate"]
    q = (1 - (1 - 2*p)**rounds)/2
    expected = sum(comb(d, k)*q**k*(1-q)**(d-k) for k in range(d//2+1, d+1))
    sigma = (expected*(1-expected)/shots)**0.5
    assert abs(measured - expected) < 6*sigma


def test_seed_reproducibility_and_matched_shots():
    cfg = ExperimentConfig(distances=[3], physical_error_rates=[0.05], shots=5000)
    a, b = run_experiment(cfg), run_experiment(cfg)
    assert a["results"][0]["samples"] == b["results"][0]["samples"]
    assert [d["failures"] for d in a["results"][0]["decoders"]] == [d["failures"] for d in b["results"][0]["decoders"]]
    reverse = cfg.model_copy(update={"decoders": list(reversed(cfg.decoders))})
    c = run_experiment(reverse)
    assert {d["decoder"]: d["failures"] for d in a["results"][0]["decoders"]} == {d["decoder"]: d["failures"] for d in c["results"][0]["decoders"]}


def test_wilson_zero_is_not_certainty():
    low, high = wilson(0, 10000)
    assert low < 1e-15
    assert 0.0003 < high < 0.0004


@pytest.mark.parametrize("values", [dict(distances=[4]), dict(distances=[3,3]), dict(physical_error_rates=[float('nan')]), dict(code="surface_x"), dict(decoders=[]), dict(shots=999999), dict(distances=[15], rounds=30, shots=200000, code="surface_x", decoders=["mwpm"])])
def test_invalid_config(values):
    with pytest.raises(ValueError):
        ExperimentConfig(**values)
