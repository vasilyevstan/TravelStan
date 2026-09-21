"""Search form.

Validation messages are generic and never echo submitted values.
"""

from __future__ import annotations

import datetime as dt
import re

from django import forms

from .domain import (
    IATA_PATTERN,
    MAX_FLEXIBILITY,
    MIN_FLEXIBILITY,
    CabinClass,
    LuggageChoice,
    SearchMode,
    SearchQuery,
)

IATA_RE = re.compile(IATA_PATTERN)
LOCATION_ID_RE = re.compile(r"^(?:[A-Z]{3}|/[mg]/[A-Za-z0-9_-]+)$")
LOCATION_SET_RE = re.compile(r"^[A-Z]{3}(?:,[A-Z]{3}){0,19}$")

ERROR_LOCATION = (
    "Choose a city or airport from the suggestions, or enter a three-letter "
    "airport code."
)
ERROR_SAME_AIRPORT = "Origin and destination must not include the same airport."
ERROR_DEPARTURE_PAST = "Departure date must be later than today."
ERROR_RETURN_ORDER = "Return date must be later than the departure date."
ERROR_FLEX_RANGE = "Choose a flexibility between 1 and 7 days."
ERROR_REQUIRED = "This field is required."
ERROR_CHOICE = "Choose one of the available options."
ERROR_DATE_INVALID = "Enter a valid date."

CABIN_CHOICES = (
    (CabinClass.ECONOMY.value, "Economy"),
    (CabinClass.PREMIUM_ECONOMY.value, "Economy+ / Premium Economy"),
    (CabinClass.BUSINESS.value, "Business"),
    (CabinClass.ALL_CLASSES.value, "All classes"),
)

MODE_CHOICES = (
    (SearchMode.EXACT.value, "Exact dates"),
    (SearchMode.FLEXIBLE.value, "Flexible dates"),
)

LUGGAGE_CHOICES = (
    (LuggageChoice.CHECKED_REQUIRED.value, "I need a checked bag included"),
    (
        LuggageChoice.NO_CHECKED_REQUIREMENT.value,
        "I do not need a checked bag included",
    ),
)


class BlankFriendlyDateField(forms.DateField):
    """Treats a whitespace-only value as blank so returns normalize to None."""

    def to_python(self, value: object) -> dt.date | None:
        if isinstance(value, str) and not value.strip():
            return None
        return super().to_python(value)


class SearchForm(forms.Form):
    origin = forms.CharField(
        label="From",
        max_length=100,
        error_messages={"required": ERROR_REQUIRED, "max_length": ERROR_LOCATION},
    )
    origin_id = forms.CharField(required=False, max_length=100)
    origin_airports = forms.CharField(required=False, max_length=79)
    destination = forms.CharField(
        label="To",
        max_length=100,
        error_messages={"required": ERROR_REQUIRED, "max_length": ERROR_LOCATION},
    )
    destination_id = forms.CharField(required=False, max_length=100)
    destination_airports = forms.CharField(required=False, max_length=79)
    departure_date = BlankFriendlyDateField(
        label="Departure date",
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"required": ERROR_REQUIRED, "invalid": ERROR_DATE_INVALID},
    )
    return_date = BlankFriendlyDateField(
        label="Return date (leave blank for one-way)",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        error_messages={"invalid": ERROR_DATE_INVALID},
    )
    cabin = forms.ChoiceField(
        label="Cabin class",
        choices=CABIN_CHOICES,
        initial=CabinClass.ECONOMY.value,
        error_messages={"required": ERROR_REQUIRED, "invalid_choice": ERROR_CHOICE},
    )
    mode = forms.ChoiceField(
        label="Date mode",
        choices=MODE_CHOICES,
        initial=SearchMode.EXACT.value,
        widget=forms.RadioSelect,
        error_messages={"required": ERROR_REQUIRED, "invalid_choice": ERROR_CHOICE},
    )
    flexibility = forms.IntegerField(
        label="Flexibility (days, 1-7)",
        required=False,
        min_value=MIN_FLEXIBILITY,
        max_value=MAX_FLEXIBILITY,
        error_messages={
            "invalid": ERROR_FLEX_RANGE,
            "min_value": ERROR_FLEX_RANGE,
            "max_value": ERROR_FLEX_RANGE,
        },
    )
    luggage = forms.ChoiceField(
        label="Checked luggage requirement",
        choices=LUGGAGE_CHOICES,
        widget=forms.RadioSelect,
        error_messages={"required": ERROR_REQUIRED, "invalid_choice": ERROR_CHOICE},
    )

    def __init__(
        self,
        *args: object,
        today: dt.date,
        allow_location_sets: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.today = today
        self.allow_location_sets = allow_location_sets

    def clean_departure_date(self) -> dt.date:
        departure = self.cleaned_data["departure_date"]
        if departure <= self.today:
            raise forms.ValidationError(ERROR_DEPARTURE_PAST)
        return departure

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        for field_name in ("origin", "destination"):
            raw_value = str(cleaned.get(field_name) or "").strip()
            direct_code = raw_value.upper()
            selected_value = str(cleaned.get(f"{field_name}_id") or "").strip()
            selected_airports = (
                str(cleaned.get(f"{field_name}_airports") or "").strip().upper()
            )
            if IATA_RE.fullmatch(direct_code):
                identifier = direct_code
                label = direct_code
                airports = (direct_code,)
            elif (
                self.allow_location_sets
                and LOCATION_ID_RE.fullmatch(selected_value)
                and LOCATION_SET_RE.fullmatch(selected_airports)
            ):
                identifier = selected_value
                label = raw_value
                airports = tuple(dict.fromkeys(selected_airports.split(",")))
                if IATA_RE.fullmatch(identifier) and identifier not in airports:
                    self.add_error(field_name, ERROR_LOCATION)
                    continue
            else:
                if field_name in cleaned:
                    self.add_error(field_name, ERROR_LOCATION)
                continue
            cleaned[field_name] = identifier
            cleaned[f"{field_name}_label"] = label
            cleaned[f"{field_name}_airports"] = airports

        origin = cleaned.get("origin_airports")
        destination = cleaned.get("destination_airports")
        if origin and destination and set(origin) & set(destination):
            self.add_error("destination", ERROR_SAME_AIRPORT)

        departure = cleaned.get("departure_date")
        return_date = cleaned.get("return_date")
        if departure and return_date and return_date <= departure:
            self.add_error("return_date", ERROR_RETURN_ORDER)

        mode = cleaned.get("mode")
        flexibility = cleaned.get("flexibility")
        if mode == SearchMode.EXACT.value:
            cleaned["flexibility"] = 0
        elif mode == SearchMode.FLEXIBLE.value:
            if flexibility is None:
                self.add_error("flexibility", ERROR_FLEX_RANGE)
        return cleaned

    def to_query(self) -> SearchQuery:
        data = self.cleaned_data
        return SearchQuery(
            origin=data["origin"],
            destination=data["destination"],
            departure_date=data["departure_date"],
            return_date=data["return_date"] or None,
            cabin=CabinClass(data["cabin"]),
            mode=SearchMode(data["mode"]),
            flexibility=int(data["flexibility"] or 0),
            luggage=LuggageChoice(data["luggage"]),
            adults=1,
            origin_label=data["origin_label"],
            destination_label=data["destination_label"],
            origin_airports=data["origin_airports"],
            destination_airports=data["destination_airports"],
        )
