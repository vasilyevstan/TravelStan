"""Bounded SerpApi Google Flights location suggestions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .providers.base import ProviderError
from .providers.http import request_json
from .providers.normalization import as_list, as_mapping, first_value

ALLOWED_API_HOSTS = ("serpapi.com",)
IATA_RE = re.compile(r"^[A-Z]{3}$")
AIRPORT_NAME_RE = re.compile(r"\b(?:airport|aerodrome|airfield)\b", re.IGNORECASE)
MAX_AIRPORTS_PER_CITY = 8
MAX_LOCATION_OPTIONS = 10


@dataclass(frozen=True, slots=True)
class LocationSuggestion:
    value: str
    label: str
    detail: str
    kind: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def search_locations(
    query: str,
    *,
    api_key: str,
    endpoint: str,
    country: str,
    locale: str,
) -> tuple[LocationSuggestion, ...]:
    term = query.strip()
    if not 2 <= len(term) <= 60:
        return ()
    payload = request_json(
        "GET",
        endpoint,
        headers={"accept": "application/json"},
        params={
            "engine": "google_flights_autocomplete",
            "q": term,
            "gl": country.lower(),
            "hl": locale.split("-", maxsplit=1)[0].lower(),
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
        for raw_airport in as_list(suggestion.get("airports"))[:MAX_AIRPORTS_PER_CITY]:
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

        if len(airports) > 1 and name:
            codes = ",".join(airport["code"] for airport in airports)
            append(
                LocationSuggestion(
                    value=codes,
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
                    label=airport["name"],
                    detail=" · ".join(detail_parts),
                    kind="airport",
                )
            )

        suggestion_id = str(suggestion.get("id") or "").strip().upper()
        if not airports and IATA_RE.fullmatch(suggestion_id):
            append(
                LocationSuggestion(
                    value=suggestion_id,
                    label=name or suggestion_id,
                    detail=description or suggestion_id,
                    kind="airport",
                )
            )

        if len(options) >= MAX_LOCATION_OPTIONS:
            break
    return tuple(options)
