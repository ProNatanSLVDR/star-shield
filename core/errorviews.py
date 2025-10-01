from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import render


def error_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    try:
        return render(request, "404.html", status=404)
    except Exception:
        return HttpResponseNotFound("Page non trouvée")


def error_404_preview(request: HttpRequest) -> HttpResponse:
    return render(request, "404.html", status=200)


def error_500(request: HttpRequest) -> HttpResponse:
    try:
        return render(request, "500.html", status=500)
    except Exception:
        return HttpResponseServerError("Erreur interne du serveur")


def error_500_preview(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=200)

