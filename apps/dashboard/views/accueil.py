from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from apps.dashboard.render import starshield_render



@login_required
def accueil_view(request: HttpRequest) -> HttpResponse:

    return starshield_render(request, "accueil.html", page_name="accueil")




