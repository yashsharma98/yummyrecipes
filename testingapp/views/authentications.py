import datetime
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import (
    HttpResponseRedirect,
)
from django.shortcuts import redirect, render
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
                messages.error(request, "username already exists!!!!")
                return redirect("signup")

    return render(request, "testingapp/signup.html", {"form": form})


def login_view(request):
    user = request.user

    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user=user)
            if user.is_authenticated:
                last_login_date = user.last_login.date()
                current_date = datetime.date.today()
                dates_diff = last_login_date + timedelta(days=7)

                if current_date >= dates_diff:
                    messages.success(
                        request,
                        "Welcome back, {}".format(user.first_name),
                        extra_tags="welcome-back-message",
                    )

            next_url = request.session.pop("next_url", None)
            if next_url:
                return HttpResponseRedirect(next_url)

            return redirect("home")

        elif email is None:
            messages.error(request, "Invalid username")

        else:
            messages.error(request, "Invalid username or password")
            return redirect("login")

    return render(request, "testingapp/login.html")


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

    return render(request, "testingapp/topostlogin.html", {"recipes": recipes, "img": img})


@login_required
def delete_account(request):
    if request.method == "POST":
        # Delete the user account
        user = request.user
        user_email = user.email
        user.delete()

        # send a email for confirming the account deletion
        subject = "[Yummy Recipes] Account Deletion Confirmation"
        from_email = settings.DEFAULT_FROM_EMAIL
        recipient_list = [user_email]
        context = {
            "name": user.first_name,
        }
        html_content = render_to_string("testingapp/acc_deletion_email.html", context)
        email = EmailMultiAlternatives(subject, "", from_email, recipient_list)
        email.attach_alternative(html_content, "text/html")
        email.send()

        return redirect("login")

    return render(request, "testingapp/delete_account.html")


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
