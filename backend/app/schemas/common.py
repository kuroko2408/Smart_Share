"""Common API response schemas and pagination models."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class DataResponse(BaseModel, Generic[T]):
    """Standard success response wrapper conforming to Smart Share API contract."""

    data: T
    message: str = Field(
        default="Operation completed successfully",
        description="Human-readable operation summary",
    )


class PaginationMeta(BaseModel):
    """Metadata describing paginated result collections."""

    total: int = Field(..., ge=0, description="Total count of matching records")
    limit: int = Field(..., ge=1, description="Requested page size limit")
    offset: int = Field(..., ge=0, description="Starting record offset")
    has_more: bool = Field(..., description="Whether subsequent records exist")


class PaginatedDataResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper for collection endpoints."""

    data: list[T]
    pagination: PaginationMeta
    message: str = Field(
        default="Records retrieved successfully",
        description="Human-readable operation summary",
    )
