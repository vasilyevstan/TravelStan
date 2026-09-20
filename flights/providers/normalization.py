"""Defensive helpers for mapping provider payloads into the domain."""

from __future__ import annotations

import datetime as dt
import hashlib
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from ..domain import (
    BaggageAllowance,
    BaggageAllowances,
    BaggageSlot,
    BaggageState,
    CabinClass,
)
from .base import ProviderConfigurationError


def as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def first_value(data: Mapping[str, Any], *paths: str) -> object | None:
    for path in paths:
        current: object = data
        for key in path.split("."):
            if isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, (list, tuple)) and key.isdigit():
                index = int(key)
                if index >= len(current):
                    current = None
                    break
                current = current[index]
            else:
                current = None
                break
        if current not in (None, ""):
            return current
    return None


def decimal_value(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def int_value(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_datetime(value: object) -> dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(candidate)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def minutes_between(start: dt.datetime, end: dt.datetime) -> int:
    return max(0, int((end - start).total_seconds() // 60))


def cabin_from_value(value: object) -> CabinClass:
    normalized = str(value or "").upper().replace("_", "").replace(" ", "")
    if normalized in {"PREMIUM", "PREMIUMECONOMY", "S"}:
        return CabinClass.PREMIUM_ECONOMY
    if normalized in {"BUSINESS", "J", "C"}:
        return CabinClass.BUSINESS
    return CabinClass.ECONOMY


def unknown_baggage() -> BaggageAllowances:
    return BaggageAllowances(
        personal_item=BaggageAllowance(BaggageSlot.PERSONAL_ITEM, BaggageState.UNKNOWN),
        carry_on=BaggageAllowance(BaggageSlot.CARRY_ON, BaggageState.UNKNOWN),
        checked_bag=BaggageAllowance(BaggageSlot.CHECKED_BAG, BaggageState.UNKNOWN),
        extra_paid_bag=BaggageAllowance(
            BaggageSlot.EXTRA_PAID_BAG, BaggageState.UNKNOWN
        ),
    )


def allowance_from_values(
    slot: BaggageSlot,
    *,
    quantity: object = None,
    explicitly_included: bool | None = None,
    weight: object = None,
    weight_unit: object = None,
    price: object = None,
    price_currency: object = None,
    price_is_binding: bool = False,
    price_scope: str | None = None,
) -> BaggageAllowance:
    parsed_quantity = int_value(quantity)
    if explicitly_included is True:
        state = BaggageState.INCLUDED
    elif explicitly_included is False:
        state = BaggageState.NOT_INCLUDED
    elif parsed_quantity is not None:
        state = (
            BaggageState.INCLUDED if parsed_quantity > 0 else BaggageState.NOT_INCLUDED
        )
    else:
        state = BaggageState.UNKNOWN
    return BaggageAllowance(
        slot=slot,
        state=state,
        quantity=parsed_quantity,
        price_amount=decimal_value(price),
        price_currency=str(price_currency) if price_currency else None,
        price_is_binding=price_is_binding,
        price_scope=price_scope,
        weight_amount=decimal_value(weight),
        weight_unit=str(weight_unit).lower() if weight_unit else None,
    )


def safe_purchase_url(value: object, allowed_hosts: Sequence[str]) -> str | None:
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    allowed = any(host == item or host.endswith(f".{item}") for item in allowed_hosts)
    if parsed.scheme != "https" or not allowed:
        return None
    return value


def validated_endpoint(value: str, allowed_hosts: Sequence[str]) -> str:
    endpoint = safe_purchase_url(value, allowed_hosts)
    if endpoint is None:
        raise ProviderConfigurationError("Provider endpoint is not permitted.")
    return endpoint


def stable_offer_id(source: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{source}-{digest}"
