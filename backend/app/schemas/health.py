"""Health check schemas."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Schema for health endpoint response."""

    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    service: str = "smart-share-backend"
