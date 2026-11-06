"""API v1 router registration."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, profiles, ride_requests

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(profiles.router)
api_router.include_router(ride_requests.router)

__all__ = ["api_router"]
