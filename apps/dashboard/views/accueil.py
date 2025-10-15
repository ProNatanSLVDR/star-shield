from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from auths.models import GoogleCredentials
from googleapiclient.discovery import build





@login_required
def accueil_view(request: HttpRequest) -> HttpResponse:

    return render(request, "accueil.html")




