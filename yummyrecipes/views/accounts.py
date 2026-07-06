from datetime import date

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth import (
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    SetPasswordForm,
)
from django.shortcuts import redirect, render

from ..decorators import login_or_guest_required
from ..forms import (
    EmailNotificationForm,
    PreferencesForm,
    Updatepro,
    Updateview,
    YearlyGoal,
    YearlyGoalForm,
)
from ..models import (
    post,
    profile,
)


# @login_required(login_url='login')
@login_or_guest_required
def profile_view(request):
    if not request.guest_active:
        user = request.user
        last_login = user.last_login

        return render(
            request,
            "yummyrecipes/profile.html",
            {
                "user": user,
                "last_login": last_login,
            },
        )

    else:
        return render(request, "yummyrecipes/profile.html")


@login_required(login_url="login")
def profile_details_partial(request):
    return render(
        request,
        "yummyrecipes/profile/partials/personal_details.html",
        {
            "user": request.user,
        },
    )


def render_account_settings(request, full_page=False):
    profile = request.user.profile
    current_year = date.today().year

    yearly_goal, _ = YearlyGoal.objects.get_or_create(
        profile=profile,
        year=current_year,
    )

    # Current year's goal
    goal_for_year = YearlyGoal.objects.filter(
        profile=profile,
        year=current_year,
    ).first()

    goal_for_year_value = goal_for_year.goal if goal_for_year else 0

    # Recipes uploaded this year
    recipes_uploaded = post.objects.filter(
        author=request.user,
        date_post__year=current_year,
    ).count()

    # Progress percentage
    progress_percentage = (recipes_uploaded / goal_for_year_value) * 100 if goal_for_year_value > 0 else 0

    context = {
        "form": EmailNotificationForm(initial={"send_email": profile.send_email}),
        "preference_form": PreferencesForm(instance=profile),
        "goal_form": YearlyGoalForm(instance=yearly_goal),
        "all_goals": profile.yearly_goals.order_by("-year"),
        "current_year": current_year,
        "recipes_uploaded": recipes_uploaded,
        "goal_for_year": goal_for_year_value,
        "progress_percentage": int(progress_percentage),
    }

    return render(
        request,
        "yummyrecipes/profile/partials/account_settings.html",
        context,
    )


@login_required(login_url="login")
def acc_settings(request):
    profile = request.user.profile
    current_year = date.today().year

    yearly_goal, _ = YearlyGoal.objects.get_or_create(
        profile=profile,
        year=current_year,
    )

    if request.method == "POST":
        # Email Notifications
        if "email_form" in request.POST:
            form = EmailNotificationForm(request.POST)

            if form.is_valid():
                profile.send_email = form.cleaned_data.get(
                    "send_email",
                    False,
                )

                profile.save()

                if request.htmx:
                    return render_account_settings(request)

                return redirect("account_settings")

        # Recipe Preferences
        elif "preference_form" in request.POST:
            preference_form = PreferencesForm(
                request.POST,
                instance=profile,
            )

            if preference_form.is_valid():
                preference_form.save()

                messages.success(
                    request,
                    "Preferences updated.",
                    extra_tags="preference-set-message",
                )

                if request.htmx:
                    return render_account_settings(request)

                return redirect("account_settings")

        # Recipe Goal
        elif "recipes_goal" in request.POST:
            goal_form = YearlyGoalForm(
                request.POST,
                instance=yearly_goal,
            )

            if goal_form.is_valid():
                goal_form.save()

                messages.success(
                    request,
                    "Goal updated.",
                    extra_tags="recipes-goal-message",
                )

                if request.htmx:
                    return render_account_settings(request)

                return redirect("account_settings")

    if request.htmx:
        return render_account_settings(request)

    return render_account_settings(
        request,
        full_page=True,
    )


@login_required(login_url="login")
def UpdateProfile(request):
    if request.method == "POST":
        update_profile = Updatepro(
            request.POST,
            instance=request.user,
        )
        update_view = Updateview(
            request.POST,
            request.FILES,
            instance=request.user.profile,
        )

        if update_profile.is_valid() and update_view.is_valid():
            update_profile.save()
            update_view.save()

            if request.htmx:
                return profile_details_partial(request)

            return redirect("profile")

    else:
        update_profile = Updatepro(instance=request.user)
        update_view = Updateview(instance=request.user.profile)

    return render(
        request,
        "yummyrecipes/profile/partials/edit_profile.html",
        {
            "update_profile": update_profile,
            "update_view": update_view,
            "gender_choices": profile.GENDER_CHOICES,
        },
    )


@login_required(login_url="login")
def UpdatePassword(request):
    user = request.user
    social_account_signup = SocialAccount.objects.filter(user=user).exists()

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)

        if form.is_valid():
            new_password = form.cleaned_data["new_password1"]

            if user.check_password(new_password):
                messages.error(
                    request,
                    "The new password cannot be the same as the old password.",
                    extra_tags="form_error_msg",
                )

            else:
                form.save()
                update_session_auth_hash(request, form.user)

                if request.htmx:
                    return profile_details_partial(request)

                return redirect("profile")

    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "yummyrecipes/profile/partials/password.html",
        {
            "form": form,
            "social_account_signup": social_account_signup,
        },
    )
