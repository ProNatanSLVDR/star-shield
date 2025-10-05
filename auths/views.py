from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_not_required
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from django.utils.translation import gettext_lazy as _


@login_not_required
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:accueil")

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

                    return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            messages.error(request, _("Email ou mot de passe incorrect."))
    else:
        form = UserLoginForm()

    context = {"form": form}
    return render(request, "auth/login.html", context)



@require_http_methods(["GET"])
def logout_view(request):
    logout(request)
    return redirect("auths:login")

