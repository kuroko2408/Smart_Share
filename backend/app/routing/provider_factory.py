"""Factory: select routing provider based on configuration."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.routing.base import RoutingProvider
from app.routing.fallback import FallbackRoutingProvider
from app.routing.ors_provider import ORSRoutingProvider
from app.routing.osrm_provider import OSRMRoutingProvider

logger = logging.getLogger(__name__)


def get_routing_provider() -> RoutingProvider:
    """
    Return the appropriate routing provider based on application settings.
    Falls back to the tortuosity provider if no API key is configured.
    """
    settings = get_settings()
    provider_name = settings.ROUTING_PROVIDER.strip().lower()
    if provider_name == "fallback":
        logger.info("Using explicitly configured geographic fallback routing.")
        return FallbackRoutingProvider()
    if settings.ROUTING_API_KEY and settings.ROUTING_API_KEY.strip():
        logger.info("Using ORS routing provider.")
        return ORSRoutingProvider(
            api_key=settings.ROUTING_API_KEY,
            timeout_seconds=settings.ROUTING_TIMEOUT_SECONDS,
        )
    if provider_name in {"", "osrm"}:
        logger.info("Using public OSRM routing; requests are rate limited.")
        return OSRMRoutingProvider(
            base_url=settings.OSRM_BASE_URL,
            timeout_seconds=settings.ROUTING_TIMEOUT_SECONDS,
        )
    logger.info("No ROUTING_API_KEY configured; using fallback tortuosity provider.")
    return FallbackRoutingProvider()
