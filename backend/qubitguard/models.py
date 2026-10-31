from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ExperimentConfig(BaseModel):
    name: str = Field(default="Distance scaling experiment", min_length=1, max_length=100)
    code: Literal["repetition", "surface_x", "surface_z"] = "repetition"
    distances: list[int] = Field(default_factory=lambda: [3, 5, 7], min_length=1, max_length=5)
    physical_error_rates: list[float] = Field(default_factory=lambda: [0.01, 0.03, 0.05], min_length=1, max_length=6)
    rounds: int = Field(default=5, ge=1, le=30)
    shots: int = Field(default=10000, ge=100, le=200000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    decoders: list[Literal["mwpm", "majority", "identity"]] = Field(default_factory=lambda: ["mwpm", "majority"], min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_sweep(self):
        if any(d < 3 or d > 15 or d % 2 == 0 for d in self.distances):
            raise ValueError("Distances must be odd integers from 3 to 15")
        if any(not 0 <= p <= 0.2 for p in self.physical_error_rates):
            raise ValueError("Physical error rates must be finite and between 0 and 0.2")
        for values in (self.distances, self.physical_error_rates, self.decoders):
            if len(set(values)) != len(values):
                raise ValueError("Sweep values and decoders must be unique")
        if self.code != "repetition" and "majority" in self.decoders:
            raise ValueError("Majority decoder is available only for repetition codes")
        cells = len(self.distances) * len(self.physical_error_rates)
        detectors = (max(self.distances) ** 2 if self.code != "repetition" else max(self.distances)) * (self.rounds + 1)
        if cells * self.shots > 2000000 or cells * self.shots * detectors > 80000000:
            raise ValueError("Sweep exceeds local work budget; reduce shots, rounds or distances")
        return self
