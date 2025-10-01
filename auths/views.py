from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_not_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .forms import UserLoginForm, UserRegistrationForm

from django.utils.translation import gettext_lazy as _


@login_not_required
@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = authenticate(request=request, email=email, password=password)

            if user is None:
                messages.error(request, _("Email ou mot de passe incorrect."))
            else:
                if not user.is_active:
                    messages.error(request, _("Ce compte est inactif."))
                else:
                    login(request, user)
                    return redirect("dashboard")
        else:
            messages.error(request, _("Email ou mot de passe incorrect."))
    else:
        form = UserLoginForm()

    return render(request, "auth/login.html", {"form": form})


@login_not_required
@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            authenticated_user = authenticate(
                request=request,
                email=user.email,
                password=form.cleaned_data["password1"],
            )

            if authenticated_user is not None and authenticated_user.is_active:
                login(request, authenticated_user)
                messages.success(request, _("Votre compte a été créé avec succès."))
                return redirect("dashboard")
        else:
            messages.error(request, _("Merci de corriger les erreurs signalées."))
    else:
        form = UserRegistrationForm()

    return render(request, "auth/register.html", {"form": form})


@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("auths:login")

