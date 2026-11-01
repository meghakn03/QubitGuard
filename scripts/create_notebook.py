"""Generate and execute the small dependency-light learning notebook."""
import contextlib
import io
import json
from pathlib import Path

cells = []
namespace = {}


def markdown(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)})


def code(source):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(source, '<notebook>', 'exec'), namespace)
    cells.append({"cell_type": "code", "metadata": {}, "execution_count": sum(c['cell_type'] == 'code' for c in cells) + 1,
        "source": source.splitlines(keepends=True), "outputs": [{"output_type": "stream", "name": "stdout", "text": output.getvalue().splitlines(keepends=True)}]})


markdown('''# QubitGuard: a first quantum error correction experiment

This notebook runs real Stim simulations using QubitGuard's engine. Install the project with `pip install -e .` in the notebook kernel's environment first. Jupyter is optional and is not needed by the web app.

An X error flips a computational basis value; a Z error flips phase. A bit-flip repetition code encodes a logical value across an odd number of data qubits and checks neighboring Z parities. It protects one error type. A surface code uses both X- and Z-type stabilizers to protect arbitrary Pauli errors. Neither encoding means copying an arbitrary unknown quantum state.

We begin with the repetition model: independent data X errors and noisy parity measurements each round, ideal parity gates and ideal final data readout. The full assumptions are in `docs/science.md`.''')
code('''import numpy as np
from math import comb
from qubitguard.engine import build_circuit, majority_decode, run_experiment
from qubitguard.models import ExperimentConfig

circuit = build_circuit('repetition', distance=3, rounds=3, p=0.05)
print(f'{circuit.num_qubits} physical qubits, {circuit.num_detectors} detectors, {circuit.num_observables} observable')
print(circuit)
''')
markdown('''## Detection events and logical observables

A detector is an expected parity relation. A detection event occurs when that relation is violated. Comparing successive noisy checks helps distinguish changes over time. A detector is evidence of an error, not a unique physical error location. The final detector layer closes the memory experiment using ideal data readout.

The decoder receives only the detection events. The sampled observable is used afterward to score recovery. It is not an input to decoding.''')
code('''syndrome, actual = circuit.compile_detector_sampler(seed=42).sample(12, separate_observables=True)
predicted = majority_decode(syndrome, distance=3, rounds=3)
print('shot | detection event indices | actual flip | predicted flip | recovered')
for i in range(12):
    print(i, np.flatnonzero(syndrome[i]).tolist(), int(actual[i, 0]), int(predicted[i, 0]), bool(actual[i, 0] == predicted[i, 0]), sep=' | ')
''')
markdown('''## Benchmark identical shots with two decoders

Majority vote reconstructs final bit patterns from parity checks and selects the lower-weight pattern. Its temporal XOR cancels intermediate readout noise, but discards useful history. MWPM uses a weighted detector graph to explain the entire event history.

Logical error rate means wrong logical predictions divided by shots for the whole memory experiment. Wilson confidence intervals quantify finite-sampling uncertainty; zero failures is not proof of a zero underlying failure probability.''')
code('''config = ExperimentConfig(distances=[3, 5, 7], physical_error_rates=[0.01, 0.03, 0.05], rounds=5, shots=10000, seed=42)
result = run_experiment(config)
print('distance | physical p | decoder | failures / shots | logical rate | 95% CI')
for cell in result['results']:
    for decoder in cell['decoders']:
        lo, hi = decoder['confidence_interval']
        print(f"{cell['distance']:8d} | {cell['physical_error_rate']:.2f} | {decoder['decoder']:8s} | {decoder['failures']:4d} / {cell['shots']} | {decoder['logical_error_rate']:.5f} | [{lo:.5f}, {hi:.5f}]")
''')
markdown('''## An independent analytic check

After `r` rounds, independent data X errors accumulate to an odd parity with probability `q = (1 - (1 - 2p)^r) / 2`. For odd distance `d`, majority fails when more than half of the data bits have flipped. This gives a binomial tail that we can compare to the simulator. This expression applies to this ideal-final-readout baseline, not the surface-code MWPM experiment.''')
code('''p, r = 0.05, config.rounds
q = (1 - (1 - 2*p)**r) / 2
for cell in result['results']:
    if cell['physical_error_rate'] != p:
        continue
    d = cell['distance']
    expected = sum(comb(d, k) * q**k * (1-q)**(d-k) for k in range(d//2 + 1, d + 1))
    observed = next(x for x in cell['decoders'] if x['decoder'] == 'majority')
    print(f"d={d}: analytic={expected:.5f}, sampled={observed['logical_error_rate']:.5f}, CI={observed['confidence_interval']}")
print('Versions:', result['provenance']['versions'])
''')
markdown('''## Next experiments

1. Increase shots when confidence intervals are wide. Record root seed, versions and batch size.
2. Add the `identity` decoder to measure the no-correction baseline.
3. Try `code='surface_z'` with `decoders=['mwpm', 'identity']` at p=0.001 and p=0.005. Its circuit-level model differs from the repetition model.
4. Compare fixed rounds with rounds proportional to distance in separate runs. Explain the changed experiment duration.

Distance suppression under this model is useful evidence, but a finite sweep does not establish a hardware threshold. Batch timing is throughput on the host CPU, not real-time hardware decoder latency.

Primary references: [Stim](https://github.com/quantumlib/Stim), [PyMatching](https://pymatching.readthedocs.io/en/stable/), and [Deltakit](https://github.com/Deltakit/deltakit).''')
notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": __import__('platform').python_version()}}, "nbformat": 4, "nbformat_minor": 5}
for i, cell in enumerate(cells):
    cell['id'] = f'qubitguard-{i:02d}'
Path('notebooks/01_qec_fundamentals.ipynb').write_text(json.dumps(notebook, indent=2) + '\n')
print('Executed and wrote notebooks/01_qec_fundamentals.ipynb')
