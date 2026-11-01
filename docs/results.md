# Recorded benchmark results

These are actual local simulation results, not illustrative dashboard values. Full machine metadata, seeds, decoder timings and samples are checked in alongside the configurations. Timings depend on host load; results are not hardware performance claims.

## Repetition distance scaling

100,000 shots per point; five rounds; root seed 42. Phenomenological bit-flip noise, with ideal gates and final readout.

| Physical p | Distance | MWPM failures | MWPM logical rate | 95% Wilson interval | Majority logical rate | No correction |
|---|---|---|---|---|---|---|
| 1% | 3 | 437 | 0.4370% | [0.3980%, 0.4798%] | 0.6350% | 4.9230% |
| 1% | 5 | 28 | 0.0280% | [0.0194%, 0.0405%] | 0.0900% | 4.8710% |
| 1% | 7 | 1 | 0.0010% | [0.0002%, 0.0057%] | 0.0170% | 4.8590% |
| 3% | 3 | 3537 | 3.5370% | [3.4243%, 3.6533%] | 4.8550% | 13.2880% |
| 3% | 5 | 584 | 0.5840% | [0.5386%, 0.6332%] | 1.9190% | 13.2820% |
| 3% | 7 | 129 | 0.1290% | [0.1086%, 0.1532%] | 0.8100% | 13.2050% |
| 5% | 3 | 8503 | 8.5030% | [8.3317%, 8.6775%] | 10.7370% | 20.3290% |
| 5% | 5 | 2535 | 2.5350% | [2.4394%, 2.6343%] | 6.1990% | 20.5180% |
| 5% | 7 | 844 | 0.8440% | [0.7892%, 0.9026%] | 3.5810% | 20.5430% |

Increasing distance suppresses the observed MWPM failure rate at each tested p. The majority baseline also benefits from distance, while discarding intermediate history. The no-correction observable flip probability does not receive the same distance protection. These are finite-shot observations under one model, not a threshold estimate.

## Rotated surface Z memory

10,000 shots per point; five rounds; root seed 42. All four configured circuit noise channels use p.

| Physical p | Distance | MWPM failures | MWPM logical rate | 95% Wilson interval |
|---|---|---|---|---|
| 0.1% | 3 | 7 | 0.0700% | [0.0339%, 0.1444%] |
| 0.1% | 5 | 2 | 0.0200% | [0.0055%, 0.0729%] |
| 0.1% | 7 | 0 | 0.0000% | [0.0000%, 0.0384%] |
| 0.5% | 3 | 268 | 2.6800% | [2.3812%, 3.0152%] |
| 0.5% | 5 | 146 | 1.4600% | [1.2429%, 1.7144%] |
| 0.5% | 7 | 55 | 0.5500% | [0.4228%, 0.7152%] |

The surface model includes noisy gates, reset and terminal measurement; do not directly equate its p with repetition p. More shots are needed for precise estimates at the lowest failure probabilities.

## Rerun

```sh
qubitguard-benchmark benchmarks/repetition-scaling.json --output data/repetition.json
qubitguard-benchmark benchmarks/surface-scaling.json --output data/surface.json
```

The output JSON includes `config`, `results`, and `provenance`. Exact sampled streams require a matching Stim execution environment and batching; rates can fluctuate across architectures even with the same root seed. See [scientific methodology](science.md).
