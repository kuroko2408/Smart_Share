"""Immutable in-memory registry for approved fare model configuration."""

from app.fares.models import FareModelConfig


class FareModelRegistry:
    def __init__(self, models: tuple[FareModelConfig, ...] | None = None) -> None:
        self._models = models or (FareModelConfig(),)

    def resolve(self, model_id: str = "mumbai_taxi_standard") -> FareModelConfig:
        for model in self._models:
            if model.model_id == model_id:
                return model
        raise LookupError(f"No fare model registered for {model_id!r}")


fare_model_registry = FareModelRegistry()
