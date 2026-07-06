import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render, resolve_url
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.cache import cache_control

from ..forms import registration_form
from ..models import (
    post,
)
from ..utils.email_utils import send_welcome_email


def signup_view(request):
    form = registration_form()

    if request.method == "POST":
        form = registration_form(request.POST)
        if form.is_valid():
            if not form.user_exit():
                form.save()

                email = form.cleaned_data["email"]
                name = form.cleaned_data["fname"]
                send_welcome_email(request, email, name)

                return redirect("login")
            else:
                messages.set_level(request, messages.DEBUG)
                messages.error(request, "username already exists!", extra_tags="signup-error")
                return redirect("signup")

    return render(request, "yummyrecipes/signup.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)

        if user is not None:
            first_name = user.first_name or user.email

            login(request, user=user)

            next_url = request.session.pop("next_url", None)
            redirect_url = next_url or resolve_url("home")

            context = {
                "login_success_name": first_name,
                "redirect_url": redirect_url,
            }

            if request.headers.get("HX-Request"):
                return render(
                    request,
                    "yummyrecipes/partials/login_header.html",
                    context,
                )

            return redirect(redirect_url)

        context = {
            "login_error": "Invalid username or password",
        }

        if request.headers.get("HX-Request"):
            return render(
                request,
                "yummyrecipes/partials/login_header.html",
                context,
            )

        messages.error(request, "Invalid username or password", extra_tags="login-error")
        return redirect("login")

    return render(request, "yummyrecipes/login.html")


@cache_control(no_cache=True, must_revalidate=True)
def logout_view(request):
    guest_uuid = request.session.get("guest_user", {}).get("uuid")
    logout(request)
    request.session.flush()

    next_page = request.GET.get("next")
    if next_page == "signup":
        response = redirect("signup")
    else:
        response = redirect("login")

    if guest_uuid:
        response.set_cookie("guest_uuid_to_clear", guest_uuid, max_age=60)  # short-lived cookie
    return response


def topostlogin(request, pk):
    recipes = post.objects.get(pk=pk)

    img = recipes.photo_set.first()

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user=user)
            return redirect("viewpost", pk)

        elif email is None:
            messages.error(request, "Invalid username")

        else:
            messages.error(request, "Invalid username or password")
            return redirect("topostlogin", pk)

    return render(request, "yummyrecipes/topostlogin.html", {"recipes": recipes, "img": img})


@login_required
def delete_account(request):
    if request.method != "POST":
        return redirect("account_settings")

    user = request.user

    # Save details before deletion
    first_name = user.first_name
    user_email = user.email

    # Log the user out first
    logout(request)

    # Delete account
    user.delete()

    # Send confirmation email
    subject = "[Yummy Recipes] Account Deletion Confirmation"
    context = {
        "name": first_name,
    }

    html_content = render_to_string("yummyrecipes/acc_deletion_email.html", context)

    email = EmailMultiAlternatives(
        subject,
        "",
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=True)

    messages.success(request, "Your account has been permanently deleted.")

    return redirect("login")


def guest_mode_session(request):
    guest_user = request.session.get("guest_user")
    guest_active = bool(guest_user and not request.user.is_authenticated)
    return guest_user, guest_active


def guest_mode(request):
    if request.method == "POST":
        name = request.POST.get("guest_user_name", "").strip()

        guest_name = slugify(name).replace("-", "_")

        guest_uuid = str(uuid.uuid4())
        unique_id = guest_uuid[:8]
        guest_email = f"{guest_name}{unique_id}@yummyrecipes.com"

        session_start_time = timezone.now()
        formatted_date = session_start_time.strftime("%b. %d, %Y")

        request.session["guest_user"] = {
            "name": name,
            "email": guest_email,
            "uuid": guest_uuid,
            "formatted_date": formatted_date,
        }

        # request.session['show_guest_modal'] = True

        return redirect("home")

    return redirect("home")
