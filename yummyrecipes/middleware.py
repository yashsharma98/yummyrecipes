from django.shortcuts import redirect
from django.urls import reverse

from .views.authentications import guest_mode_session


class CheckPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            has_password = request.session.get("has_usable_password")
            if has_password is None:
                has_password = request.user.has_usable_password()
                request.session["has_usable_password"] = has_password
            if not has_password and request.path != reverse("updatepassword"):
                return redirect("updatepassword")
        return self.get_response(request)


class ClearExistingUserFirstnameMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = reverse("login")

    def __call__(self, request):
        response = self.get_response(request)
        if request.path == self.login_url:
            request.session.pop("existing_user_first_name", None)
            request.session.pop("existing_user_email", None)
        return response


class GuestMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        guest_user, guest_active = guest_mode_session(request)
        request.guest_user = guest_user
        request.guest_active = guest_active
        response = self.get_response(request)
        return response
