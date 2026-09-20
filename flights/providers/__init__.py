"""Fail-closed provider registry."""

from __future__ import annotations

from collections.abc import Sequence

from django.conf import settings

from .afkl import AirFranceKLMProvider
from .base import (
    FlightProvider,
    ProviderConfigurationError,
    ProviderNotice,
    ProviderSearchResult,
)
from .serpapi import SerpApiProvider
from .singapore import SingaporeAirlinesProvider
from .synthetic import SyntheticDemoProvider
from .tui import TUIProvider

KNOWN_PROVIDERS = {"synthetic_demo", "serpapi"}
KEY_SETTINGS = {
    "serpapi": "SERPAPI_API_KEY",
}


def configured_provider_names() -> tuple[str, ...]:
    value = getattr(settings, "TRAVELSTAN_PROVIDERS", ("synthetic_demo",))
    if isinstance(value, str):
        return tuple(item.strip().lower() for item in value.split(",") if item.strip())
    return tuple(str(item).strip().lower() for item in value if str(item).strip())


def configuration_errors() -> tuple[str, ...]:
    names = configured_provider_names()
    errors: list[str] = []
    if not names:
        errors.append("TRAVELSTAN_PROVIDERS must select at least one provider.")
    if len(names) != len(set(names)):
        errors.append("TRAVELSTAN_PROVIDERS cannot contain duplicate providers.")
    unknown = sorted(set(names) - KNOWN_PROVIDERS)
    if unknown:
        errors.append(f"Unknown TravelStan provider: {', '.join(unknown)}.")
    if "synthetic_demo" in names and len(names) > 1:
        errors.append("Synthetic and external providers cannot be enabled together.")
    for name in names:
        key_setting = KEY_SETTINGS.get(name)
        if key_setting and not getattr(settings, key_setting, ""):
            errors.append(f"{key_setting} is required when {name} is enabled.")
    return tuple(errors)


def get_providers() -> tuple[FlightProvider, ...]:
    errors = configuration_errors()
    if errors:
        raise ProviderConfigurationError(" ".join(errors))
    providers: list[FlightProvider] = []
    for name in configured_provider_names():
        if name == "synthetic_demo":
            providers.append(SyntheticDemoProvider())
        elif name == "serpapi":
            providers.append(
                SerpApiProvider(
                    settings.SERPAPI_API_KEY,
                    country=settings.TRAVELSTAN_COUNTRY,
                    locale=settings.TRAVELSTAN_LOCALE,
                    currency=settings.SERPAPI_CURRENCY,
                    endpoint=settings.SERPAPI_API_URL,
                )
            )
    return tuple(providers)


def provider_display_names(names: Sequence[str] | None = None) -> tuple[str, ...]:
    display = {
        "synthetic_demo": "TravelStan demo",
        "serpapi": "SerpApi / Google Flights",
    }
    return tuple(
        display.get(name, name) for name in (names or configured_provider_names())
    )


__all__ = [
    "AirFranceKLMProvider",
    "FlightProvider",
    "ProviderNotice",
    "ProviderSearchResult",
    "SerpApiProvider",
    "SingaporeAirlinesProvider",
    "SyntheticDemoProvider",
    "TUIProvider",
    "configuration_errors",
    "configured_provider_names",
    "get_providers",
]
