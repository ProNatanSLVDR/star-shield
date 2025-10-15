from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from auths.models import GoogleCredentials





def gmb_management_view(request: HttpRequest) -> HttpResponse:

    credentials = GoogleCredentials.objects.filter(user=request.user).prefetch_related("etablissements")

    context = {
        "credentials": credentials,
    }
    return render(request, "gmb_management.html", context)