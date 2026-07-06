from allauth.socialaccount.views import SignupView
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    LoginView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy


class CustomLoginView(LoginView):
    def get(self, request, *args, **kwargs):
        request.session.pop("existing_user_fullname", None)
        request.session.pop("existing_user_email", None)
        return super().get(request, *args, **kwargs)


class CustomPasswordResetView(PasswordResetView):
    template_name = "yummyrecipes/password_reset_form.html"
    email_template_name = "yummyrecipes/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "yummyrecipes/password_reset_done.html"


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "yummyrecipes/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "yummyrecipes/password_reset_complete.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class CustomSocialSignupView(SignupView):
    def dispatch(self, request, *args, **kwargs):
        sociallogin = self.request.session.get("socialaccount_sociallogin")
        if sociallogin:
            email = sociallogin["user"]["email"]
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                request.session["existing_user_first_name"] = existing_user.first_name
                request.session["existing_user_email"] = existing_user.email
                return redirect(reverse("login"))

        return super().dispatch(request, *args, **kwargs)
