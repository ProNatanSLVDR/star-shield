from django.http import HttpRequest, HttpResponse
from django.shortcuts import render




def accueil_view(request: HttpRequest) -> HttpResponse:

    context = {}
    return render(request, "accueil.html", context)

