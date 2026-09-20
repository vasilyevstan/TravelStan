"""Django system checks for fail-closed provider configuration."""

from __future__ import annotations

from django.core.checks import Error, register

from .providers import configuration_errors


@register()
def provider_configuration_check(**kwargs: object) -> list[Error]:
    return [
        Error(message, id=f"flights.E{index:03d}")
        for index, message in enumerate(configuration_errors(), start=1)
    ]
