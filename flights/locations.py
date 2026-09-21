"""Bounded SerpApi Google Flights location suggestions."""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any

from .providers.base import ProviderError
from .providers.http import request_json
from .providers.normalization import (
    as_list,
    as_mapping,
    first_value,
    validated_endpoint,
)

ALLOWED_API_HOSTS = ("serpapi.com",)
IATA_RE = re.compile(r"^[A-Z]{3}$")
KGMID_RE = re.compile(r"^/[mg]/[A-Za-z0-9_-]+$")
AIRPORT_NAME_RE = re.compile(r"\b(?:airport|aerodrome|airfield)\b", re.IGNORECASE)
MAX_AIRPORTS_PER_CITY = 20
MAX_LOCATION_OPTIONS = 10
MAX_LOOKUPS_PER_MINUTE = 20
MAX_LOOKUPS_PER_PROCESS = 100


@dataclass(frozen=True, slots=True)
class LocationSuggestion:
    value: str
    airports: str
    label: str
    detail: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class LocationLookupBudget:
    def __init__(
        self,
        *,
        minute_limit: int = MAX_LOOKUPS_PER_MINUTE,
        process_limit: int = MAX_LOOKUPS_PER_PROCESS,
    ) -> None:
        self.minute_limit = minute_limit
        self.process_limit = process_limit
        self._timestamps: deque[float] = deque()
        self._total = 0
        self._lock = Lock()

    def reserve(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            while self._timestamps and current - self._timestamps[0] >= 60:
                self._timestamps.popleft()
            if (
                len(self._timestamps) >= self.minute_limit
                or self._total >= self.process_limit
            ):
                return False
            self._timestamps.append(current)
            self._total += 1
            return True


location_lookup_budget = LocationLookupBudget()


def search_locations(
    query: str,
    *,
    api_key: str,
    endpoint: str,
    country: str,
) -> tuple[LocationSuggestion, ...]:
    term = query.strip()
    if not 2 <= len(term) <= 60:
        return ()
    payload = request_json(
        "GET",
        validated_endpoint(endpoint, ALLOWED_API_HOSTS),
        headers={"accept": "application/json"},
        params={
            "engine": "google_flights_autocomplete",
            "q": term,
            "gl": country.lower(),
            "hl": "en",
            "exclude_regions": "true",
            "output": "json",
            "api_key": api_key,
        },
    )
    if first_value(payload, "error"):
        raise ProviderError("Location provider returned an error.")
    return _normalize_suggestions(payload)


def _normalize_suggestions(
    payload: dict[str, Any],
) -> tuple[LocationSuggestion, ...]:
    options: list[LocationSuggestion] = []
    seen: set[str] = set()

    def append(option: LocationSuggestion) -> None:
        if option.value in seen or len(options) >= MAX_LOCATION_OPTIONS:
            return
        seen.add(option.value)
        options.append(option)

    for raw_suggestion in as_list(payload.get("suggestions")):
        suggestion = as_mapping(raw_suggestion)
        name = str(suggestion.get("name") or "").strip()
        description = str(suggestion.get("description") or "").strip()
        airports: list[dict[str, str]] = []
        for raw_airport in as_list(suggestion.get("airports")):
            airport = as_mapping(raw_airport)
            code = str(airport.get("id") or "").strip().upper()
            airport_name = str(airport.get("name") or "").strip()
            if not IATA_RE.fullmatch(code) or not AIRPORT_NAME_RE.search(airport_name):
                continue
            airports.append(
                {
                    "code": code,
                    "name": airport_name,
                    "city": str(airport.get("city") or name).strip(),
                    "distance": str(airport.get("distance") or "").strip(),
                }
            )
            if len(airports) >= MAX_AIRPORTS_PER_CITY:
                break

        suggestion_id = str(suggestion.get("id") or "").strip()
        if len(airports) > 1 and name and KGMID_RE.fullmatch(suggestion_id):
            codes = ",".join(airport["code"] for airport in airports)
            append(
                LocationSuggestion(
                    value=suggestion_id,
                    airports=codes,
                    label=f"{name} — all airports",
                    detail=", ".join(airport["code"] for airport in airports),
                    kind="city",
                )
            )

        for airport in airports:
            detail_parts = [
                part
                for part in (
                    airport["city"],
                    airport["code"],
                    airport["distance"],
                )
                if part
            ]
            append(
                LocationSuggestion(
                    value=airport["code"],
                    airports=airport["code"],
                    label=airport["name"],
                    detail=" · ".join(detail_parts),
                    kind="airport",
                )
            )

        airport_id = suggestion_id.upper()
        if not airports and IATA_RE.fullmatch(airport_id):
            append(
                LocationSuggestion(
                    value=airport_id,
                    airports=airport_id,
                    label=name or airport_id,
                    detail=description or airport_id,
                    kind="airport",
                )
            )

        if len(options) >= MAX_LOCATION_OPTIONS:
            break
    return tuple(options)
