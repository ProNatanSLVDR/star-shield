from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import EmailAuthenticationForm, UserCreationForm


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid email or password.")
    else:
        form = EmailAuthenticationForm(request)

    return render(request, "auths/login.html", {"form": form})


@login_required
@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("auths:login")


def signup_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            password = form.cleaned_data.get("password1", "")
            authenticated_user = authenticate(request=request, username=user.email, password=password)
            if authenticated_user is None:
                messages.warning(
                    request,
                    "Your account was created, but we could not log you in automatically. "
                    "Use your email and password to log in.",
                )
                return redirect("auths:login")

            login(request, authenticated_user)
            messages.success(request, "Welcome! Your account is ready.")
            return redirect("dashboard")
        messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()

    return render(request, "auths/signup.html", {"form": form})
