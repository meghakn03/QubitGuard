import argparse
import json
from pathlib import Path
from .engine import run_experiment
from .models import ExperimentConfig


def main():
    parser = argparse.ArgumentParser(description="Run a reproducible QubitGuard sweep")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = ExperimentConfig.model_validate_json(args.config.read_text())
    result = run_experiment(config, lambda done, total: print(f"Completed {done}/{total} cells", flush=True))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Results: {args.output}")


if __name__ == "__main__":
    main()
