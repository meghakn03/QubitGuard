# Scientific model and validation

## From a physical qubit to a logical memory

A qubit has a state that can be disturbed by its environment and by imperfect operations. Pauli X changes a computational basis value; Pauli Z changes its phase. Y combines both. Error correction distributes information across physical qubits to encode a logical qubit. It does not make independent copies of an unknown quantum state.

A stabilizer is an operator whose expected measurement is fixed for a valid encoded state. Compatible stabilizers can be measured together. Adjacent Z⊗Z checks in a bit-flip repetition code reveal whether neighboring bits disagree without measuring their individual values. A syndrome is the collection of check outcomes. Detection events mark deviations from expected parity, often differences between successive syndrome measurements. Measurement errors can also produce detection events.

Distance is the minimum weight of a nontrivial logical operator. An odd-distance repetition code corrects up to floor(d/2) bit flips under ideal syndrome readout. It protects against X errors only, not arbitrary quantum noise. Rotated surface codes have both X- and Z-type checks; QubitGuard measures one memory basis at a time.

## Exact experiment definitions

**Repetition:** ideal all-zero preparation; before each round, independent X_ERROR(p) on each data qubit; ideal adjacent parity extraction with reset ancillas; independent X_ERROR(p) on each ancilla immediately before readout, representing a noisy parity result. Final data readout is ideal. The first detector compares with known zero parity, intermediate detectors compare successive check outcomes, and final detectors compare final data parity with the last check result. The logical observable is the last data qubit's measurement.

This is a phenomenological bit-flip model, not a circuit-level hardware model. Parameter p is used independently for both data and parity-readout errors. A detector event does not uniquely identify a particular physical error.

**Surface X / Z:** Stim's `surface_code:rotated_memory_x` or `rotated_memory_z`, with `after_clifford_depolarization`, `before_round_data_depolarization`, `before_measure_flip_probability`, and `after_reset_flip_probability` all set to p. Unlike the repetition experiment, preparation and terminal measurements are noisy. See the generated `.stim` circuit through the API to inspect the exact sequence.

The same numerical p is therefore not an equivalent physical error budget across code families. Rounds are fixed across a sweep, independently of distance. A sweep with rounds proportional to distance would answer a different question.

## Decoders

- **Majority vote:** available only for repetition. XOR detection events over time for each check; the terms telescope to the perfect final adjacent-data parities. Reconstruct the two complementary bit patterns and choose the lower-weight one. This deliberately discards the intermediate time history. It does not use the actual logical observable as an input.
- **MWPM:** construct a PyMatching graph from `circuit.detector_error_model(decompose_errors=True)`; decode detection events using `decode_batch`. Decomposition allows graph decoding but does not preserve every correlation of a depolarizing fault. Correlation-aware matching is not enabled. MWPM is not a maximum-likelihood logical decoder in general.
- **No correction:** predict zero logical flips regardless of syndrome. This is an ablation baseline, not an active recovery algorithm.

Decoding predicts the observable flip. Recovery success means this equals Stim's sampled observable, not that the exact physical error pattern was identified. All configured decoders operate on identical sampled shots in a parameter cell.

## Rates and statistical uncertainty

The logical error rate is `number of wrong logical predictions / shots` for a complete memory experiment. It is not divided by the number of rounds. Results include two-sided 95% Wilson score intervals for a binomial proportion. These are marginal intervals for each decoder, not a paired significance test of decoder differences and not simultaneous coverage for the whole sweep.

For zero failures, a nonzero upper confidence limit remains. On a logarithmic chart the dashboard plots that upper limit as an open downward triangle, not as a measured positive failure rate. Avoid claims of a measured threshold or error-free performance from this finite sweep.

## Analytic cross-check

After r independent bit-flip rounds with probability p, a data bit has odd parity with probability

`q = [1 − (1 − 2p)^r] / 2`.

The majority decoder fails with probability

`sum(comb(d,k) q^k (1-q)^(d-k), k=floor(d/2)+1..d)`.

The test suite compares 100,000 sampled shots with this prediction within six binomial standard deviations. Other checks exhaust all bit patterns for d=3,5,7, inject a certain single data error at every location, verify zero-noise memories for both surface bases and repetition, and check seed and decoder-order invariance. These validate known cases; they do not prove correctness for arbitrary noise models.

## Timing and reproducibility

Sampling uses a seeded compiled Stim sampler, in batches of at most 4,096 shots. Each cell seed is SHA-256-derived from engine version, root seed, code, distance, rounds, and p, so sweep ordering and decoder selection do not change that cell's stream. The sampler stream still depends on Stim version, architecture/SIMD behavior, batch sizes and shot count. Record the full provenance and rerun in the same environment for exact comparisons; a seed alone does not guarantee cross-machine bit-identical output.

Graph setup and sampling time are recorded separately. Decoders are warmed on a zero-syndrome row. Decoder execution order rotates across batches. Mean decoding time is total timed decode duration divided by shots. p50/p95 are percentiles of *batch mean* per-shot times, unweighted across batches. They are not single-shot tail latency; especially small experiments have too few batches for strong percentile conclusions. These timings include output allocation and Python-to-library calls and depend on system load. They are not real-time decoder or quantum hardware measurements.

## Primary references

- [Stim repository and API](https://github.com/quantumlib/Stim)
- [PyMatching's Stim decoding workflow](https://pymatching.readthedocs.io/en/stable/)
- [Deltakit repository](https://github.com/Deltakit/deltakit)
