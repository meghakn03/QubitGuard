# Deltakit extension investigation

QubitGuard's core intentionally runs entirely on local Stim and PyMatching, with no account or cloud token. Deltakit is an optional exploration path, not an implemented third decoder or a dependency of the API.

Riverlane's [Deltakit repository](https://github.com/Deltakit/deltakit) describes circuit construction, QPU noise models, Stim conversion and local PyMatching workflows. Its [setup guide](https://deltakit-docs.riverlane.com/en/stable/setup.html) distinguishes local installation from authenticated remote services. Some online functionality requires a token; no token should be committed or embedded in a dashboard.

Use a separate Python 3.11+ virtual environment for this investigation so the validated core lock stays intact:

```sh
python3.11 -m venv .venv-deltakit
.venv-deltakit/bin/pip install '.[deltakit]'
```

The optional extra bounds the 0.10 API family. It has not been included in the core lock or validation run. If its dependency constraints conflict on your platform, follow the upstream installation guidance in a separate environment rather than changing the benchmark environment silently.

A useful extension experiment:

1. Use Deltakit's local rotated-planar memory construction and a documented toy QPU noise model.
2. Obtain its noisy Stim circuit through the supported local conversion/decoder-construction API for the installed version.
3. Save that circuit and its complete noise specification. Compare detector and observable counts with QubitGuard's Stim-generated circuit.
4. Decode the saved circuit with the same PyMatching sampling protocol and Wilson intervals used here. Record Deltakit and all transitive versions.
5. First compare the **same exported circuit** across tools. Only then compare independently constructed circuits, explaining differences in gate scheduling and noise locations. Identical values of p do not imply identical models.

Acceptance checks before integrating it into the dashboard: noiseless recovery; known injected error recovery; a deterministic same-environment seed check; metadata showing the circuit source; independent noise-model labels; no token requirement in the default local path. Follow the upstream API for your installed version; Deltakit's cloud and proprietary decoders are outside this project's implemented scope.
