"""Fail-closed provider registry."""

from __future__ import annotations

from collections.abc import Sequence

from django.conf import settings

from ..domain import DataStatus
from .afkl import AirFranceKLMProvider
from .base import (
    FlightProvider,
    ProviderConfigurationError,
    ProviderNotice,
    ProviderSearchResult,
)
from .singapore import SingaporeAirlinesProvider
from .synthetic import SyntheticDemoProvider
from .tui import TUIProvider

KNOWN_PROVIDERS = {"synthetic_demo", "afkl", "singapore", "tui"}
KEY_SETTINGS = {
    "afkl": "AFKL_API_KEY",
    "singapore": "SINGAPORE_API_KEY",
    "tui": "TUI_API_KEY",
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
    if "afkl" in names and getattr(settings, "AFKL_TRAVEL_HOST", "KL") not in {
        "AF",
        "KL",
    }:
        errors.append("AFKL_TRAVEL_HOST must be AF or KL.")
    for name in names:
        key_setting = KEY_SETTINGS.get(name)
        if key_setting and not getattr(settings, key_setting, ""):
            errors.append(f"{key_setting} is required when {name} is enabled.")
    for setting_name in (
        "AFKL_DATA_STATUS",
        "SINGAPORE_DATA_STATUS",
        "TUI_DATA_STATUS",
    ):
        try:
            status = DataStatus(getattr(settings, setting_name, "trial"))
        except ValueError:
            errors.append(f"{setting_name} must be live, trial, or sandbox.")
        else:
            if status is DataStatus.SYNTHETIC:
                errors.append(f"{setting_name} must be live, trial, or sandbox.")
    return tuple(errors)


def get_providers() -> tuple[FlightProvider, ...]:
    errors = configuration_errors()
    if errors:
        raise ProviderConfigurationError(" ".join(errors))
    providers: list[FlightProvider] = []
    for name in configured_provider_names():
        if name == "synthetic_demo":
            providers.append(SyntheticDemoProvider())
        elif name == "afkl":
            providers.append(
                AirFranceKLMProvider(
                    settings.AFKL_API_KEY,
                    host=settings.AFKL_TRAVEL_HOST,
                    country=settings.TRAVELSTAN_COUNTRY,
                    locale=settings.TRAVELSTAN_LOCALE,
                    data_status=DataStatus(settings.AFKL_DATA_STATUS),
                )
            )
        elif name == "singapore":
            providers.append(
                SingaporeAirlinesProvider(
                    settings.SINGAPORE_API_KEY,
                    country=settings.TRAVELSTAN_COUNTRY,
                    locale=settings.TRAVELSTAN_LOCALE.replace("-", "_"),
                    data_status=DataStatus(settings.SINGAPORE_DATA_STATUS),
                    endpoint=settings.SINGAPORE_API_URL,
                )
            )
        elif name == "tui":
            providers.append(
                TUIProvider(
                    settings.TUI_API_KEY,
                    currency="GBP",
                    data_status=DataStatus(settings.TUI_DATA_STATUS),
                    endpoint=settings.TUI_API_URL,
                )
            )
    return tuple(providers)


def provider_display_names(names: Sequence[str] | None = None) -> tuple[str, ...]:
    display = {
        "synthetic_demo": "TravelStan demo",
        "afkl": "Air France–KLM",
        "singapore": "Singapore Airlines",
        "tui": "TUI",
    }
    return tuple(
        display.get(name, name) for name in (names or configured_provider_names())
    )


__all__ = [
    "AirFranceKLMProvider",
    "FlightProvider",
    "ProviderNotice",
    "ProviderSearchResult",
    "SingaporeAirlinesProvider",
    "SyntheticDemoProvider",
    "TUIProvider",
    "configuration_errors",
    "configured_provider_names",
    "get_providers",
]
