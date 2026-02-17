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

        profile = request.user.profile
        if request.method == "POST":
            form = EmailNotificationForm(request.POST)
            if form.is_valid():
                send_email = form.cleaned_data.get("send_email", False)
                request.user.profile.send_email = send_email
                request.user.profile.save()
                return redirect("profile")

        form = EmailNotificationForm(initial={"send_email": profile.send_email})

        pass_success = request.session.pop("pass_success", None)

        return render(
            request,
            "testingapp/profile.html",
            {
                "user": user,
                "last_login": last_login,
                "form": form,
                "pass_success": pass_success,
            },
        )

    else:
        return render(request, "testingapp/profile.html")


@login_required(login_url="login")
def acc_settings(request):
    if not request.guest_active:
        profile = request.user.profile
        current_year = date.today().year

        yearly_goal, created = YearlyGoal.objects.get_or_create(profile=profile, year=current_year)

        if request.method == "POST":
            if "email_form" in request.POST:
                form = EmailNotificationForm(request.POST)
                if form.is_valid():
                    send_email = form.cleaned_data.get("send_email", False)

                    # Update the user's email notification preference in the database
                    request.user.profile.send_email = send_email
                    request.user.profile.save()
                    return redirect("account_settings")

            if "preference_form" in request.POST:
                preference_form = PreferencesForm(request.POST, instance=request.user.profile)
                if preference_form.is_valid():
                    preference_form.save()
                    messages.success(request, "Welcome back", extra_tags="preference-set-message")
                    return redirect("account_settings")

                else:
                    preference_form = PreferencesForm(instance=request.user.profile)

            if "recipes_goal" in request.POST:
                goal_form = YearlyGoalForm(request.POST, instance=yearly_goal)
                if goal_form.is_valid():
                    goal_form.save()
                    messages.success(request, "Recipes goal", extra_tags="recipes-goal-message")
                    return redirect("account_settings")

        user_profile = request.user.profile

        # goals set for current year
        goal_for_year = YearlyGoal.objects.filter(profile=user_profile, year=current_year).first()
        goal_for_year_value = goal_for_year.goal if goal_for_year else 0

        # recipes uploaded in current year not counting the previous years recipes
        recipes_uploaded = post.objects.filter(author=request.user, date_post__year=current_year).count()

        # progress percentage
        progress_percentage = (recipes_uploaded / goal_for_year_value) * 100 if goal_for_year_value > 0 else 0

        form = EmailNotificationForm(initial={"send_email": profile.send_email})
        preference_form = PreferencesForm(instance=request.user.profile)
        goal_form = YearlyGoalForm(instance=yearly_goal)

        all_goals = profile.yearly_goals.order_by("-year")
        return render(
            request,
            "testingapp/acc_settings.html",
            {
                "form": form,
                "preference_form": preference_form,
                "goal_form": goal_form,
                "all_goals": all_goals,
                "current_year": current_year,
                "recipes_uploaded": recipes_uploaded,
                "goal_for_year": goal_for_year_value,
                "progress_percentage": int(progress_percentage),
            },
        )

    else:
        return render(request, "testingapp/acc_settings.html")


@login_required(login_url="login")
def UpdateProfile(request):
    update_profile = Updatepro(request.POST or None, instance=request.user)
    update_view = Updateview(request.POST or None, request.FILES, instance=request.user.profile)
    if request.method == "POST":
        if update_profile.is_valid() or update_view.is_valid():
            pro = update_profile.save(commit=False)
            view = update_view.save(commit=False)
            pro.save()
            view.save()

            return redirect("profile")

        else:
            update_profile = Updatepro(instance=request.user)
            update_view = Updateview(instance=request.user.profile)

    return render(
        request,
        "testingapp/updateprofile.html",
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
            new_password = form.cleaned_data.get("new_password1")
            if user.check_password(new_password):
                form_error_msg = "The new password cannot be the same as the old password."
                messages.error(request, form_error_msg, extra_tags="form_error_msg")

            else:
                form.save()
                update_session_auth_hash(request, form.user)
                pass_success = "Your password has been updated!"
                request.session["pass_success"] = pass_success
                return redirect("profile")

    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "testingapp/updatepassword.html",
        {"form": form, "social_account_signup": social_account_signup},
    )
