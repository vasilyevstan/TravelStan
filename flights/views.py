"""Server-rendered search view.

GET renders the empty form. POST validates, plans, and renders normalized
demo offers. No request values, IP addresses, or results are stored or logged.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from .clock import current_date, current_datetime
from .forms import SearchForm
from .providers import configured_provider_names, provider_display_names
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
    context: dict[str, object] = {
        "today": today,
        "searched": False,
        "offers": (),
        "outcome": None,
        "error_message": None,
        "summary_error": None,
        "provider_names": provider_display_names(),
        "synthetic_mode": configured_provider_names() == ("synthetic_demo",),
    }

    if request.method == "POST":
        form = SearchForm(request.POST, today=today)
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
        form = SearchForm(today=today)

    context["form"] = form
    return render(request, TEMPLATE, context)
