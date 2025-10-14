from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from utils.qrcodes import generate_qrcode



def accueil_view(request: HttpRequest) -> HttpResponse:
    qrcode = generate_qrcode("https://www.google.com")

    for creds in request.user.google_credentials.all():
        gmb_accounts = creds.get_gmb_accounts()
        print(gmb_accounts)

    context = {
        "qrcode": qrcode,
    }
    return render(request, "accueil.html", context)

