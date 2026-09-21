"""Server-rendered search view.

GET renders the empty form. POST validates, plans, and renders normalized
demo offers. No request values, IP addresses, or results are stored or logged.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from .clock import current_date, current_datetime
from .forms import SearchForm
from .locations import location_lookup_budget, search_locations
from .providers import configured_provider_names, provider_display_names
from .providers.base import ProviderError
from .services import SearchUnavailable, run_search

TEMPLATE = "flights/search.html"
GENERIC_FORM_ERROR = "Check the highlighted fields and try again."


def search(
    request: HttpRequest,
    *,
    today_provider: Callable[[], dt.date] | None = None,
    now_provider: Callable[[], dt.datetime] | None = None,
) -> HttpResponse:
    today_provider = today_provider or current_date
    now_provider = now_provider or current_datetime
    today = today_provider()
    provider_names = configured_provider_names()
    smart_location_search = provider_names == ("serpapi",)
    context: dict[str, object] = {
        "today": today,
        "searched": False,
        "offers": (),
        "outcome": None,
        "error_message": None,
        "summary_error": None,
        "provider_names": provider_display_names(provider_names),
        "synthetic_mode": provider_names == ("synthetic_demo",),
        "experimental_mode": provider_names == ("serpapi",),
        "smart_location_search": smart_location_search,
    }

    if request.method == "POST":
        form = SearchForm(
            request.POST,
            today=today,
            allow_location_sets=smart_location_search,
        )
        if form.is_valid():
            query = form.to_query()
            context["query"] = query
            context["searched"] = True
            try:
                outcome = run_search(query, today=today, now=now_provider())
            except SearchUnavailable as exc:
                context["error_message"] = str(exc)
            else:
                context["outcome"] = outcome
                context["offers"] = outcome.offers
        else:
            context["summary_error"] = GENERIC_FORM_ERROR
    else:
        form = SearchForm(today=today, allow_location_sets=smart_location_search)

    context["form"] = form
    return render(request, TEMPLATE, context)


@require_POST
def location_lookup(request: HttpRequest) -> JsonResponse:
    if configured_provider_names() != ("serpapi",):
        return JsonResponse({"error": "Location lookup unavailable."}, status=404)
    if not settings.SERPAPI_API_KEY:
        return JsonResponse({"error": "Location lookup unavailable."}, status=503)
    query = request.POST.get("q", "")
    if not 2 <= len(query.strip()) <= 60:
        return JsonResponse({"suggestions": ()}, status=400)
    if not location_lookup_budget.reserve():
        response = JsonResponse({"error": "Location lookup limit reached."}, status=429)
        response["Retry-After"] = "60"
        return response
    try:
        suggestions = search_locations(
            query,
            api_key=settings.SERPAPI_API_KEY,
            endpoint=settings.SERPAPI_API_URL,
            country=settings.TRAVELSTAN_COUNTRY,
        )
    except ProviderError:
        return JsonResponse({"error": "Location lookup unavailable."}, status=503)
    response = JsonResponse(
        {"suggestions": [suggestion.as_dict() for suggestion in suggestions]}
    )
    response["Cache-Control"] = "no-store"
    return response
