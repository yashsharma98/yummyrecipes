from django.shortcuts import redirect

from .views.authentications import guest_mode_session


def login_or_guest_required(view_func):
    def user_access(request, *args, **kwargs):
        guest_status, guest_active = guest_mode_session(request)
        if request.user.is_authenticated or guest_active:
            return view_func(request, *args, **kwargs)

        request.session["next_url"] = request.get_full_path()
        return redirect("login")

    return user_access
