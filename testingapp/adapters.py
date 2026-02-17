from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if "first_name" in sociallogin.account.extra_data:
            user.first_name = sociallogin.account.extra_data["first_name"]
        if "last_name" in sociallogin.account.extra_data:
            user.last_name = sociallogin.account.extra_data["last_name"]
        user.email = sociallogin.account.extra_data.get("email", user.email)
        user.save()
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        return "/updatepassword/"
