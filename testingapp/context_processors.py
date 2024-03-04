def theme(request):
    if 'is_dark_theme' in request.session:
        is_dark_theme = request.session.get('is_dark_theme')
        return {'is_dark_theme':is_dark_theme}
    return {'is_dark_theme': False}

def colortheme(request):
    if 'color_theme' in request.session:
        color_theme = request.session.get('color_theme')
        return {'color_theme':color_theme}
    return {'color_theme': False}

def defaulttheme(request):
    if 'original_theme' in request.session:
        original_theme = request.session.get('original_theme')
        return {'original_theme':original_theme}
    return {'original_theme': False}

from django.contrib.auth.models import User
from .models import post

def search_autocomplete_data(request):
    titlesn = post.objects.all()
    userprofile = User.objects.all()

    titles = [tlist.title for tlist in titlesn]
    user_profiles = [profile.get_full_name() for profile in userprofile]
    autocomplete_list = titles + user_profiles
    

    return {'autocomplete_list': autocomplete_list}


from notifications.models import Notification

def message_notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(recipient=request.user)
    else:
        notifications = [] 
    return {'notifications': notifications}
