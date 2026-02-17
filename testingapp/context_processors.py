import datetime
import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from notifications.models import Notification

from .models import BlogHistory, post, searchedRecipesRanking

AUTOCOMPLETE_CACHE_KEY = "autocomplete_context_final"
AUTOCOMPLETE_CACHE_TTL = 60 * 60


def search_autocomplete_data(request):
    cached_data = cache.get(AUTOCOMPLETE_CACHE_KEY)
    if cached_data:
        return cached_data

    categories = ["Veg", "Non Veg"]
    cuisines = ["Indian", "Italian", "American"]
    meal_types = ["Breakfast", "Lunch", "Snacks", "Dinner"]
    difficulties = ["Easy", "Medium", "Hard"]

    timing_phrases = [
        "Quick recipes",
        "Fast recipes",
        "Under 15 minutes",
        "Under 30 minutes",
    ]

    suggestions = []

    # filter
    for category in categories:
        suggestions.append(f"{category} recipes")

    for category in categories:
        for meal in meal_types:
            suggestions.append(f"{category} {meal} recipes")

    for cuisine in cuisines:
        suggestions.append(f"{cuisine} cuisine recipes")

    for cuisine in cuisines:
        for difficulty in difficulties:
            suggestions.append(f"{cuisine} {difficulty} recipes")

    for difficulty in difficulties:
        for meal in meal_types:
            suggestions.append(f"{difficulty} {meal} recipes")

    for phrase in timing_phrases:
        suggestions.append(phrase)
        for meal in meal_types:
            suggestions.append(f"{phrase} for {meal}")

    # recipe titles
    recipe_titles = list(post.objects.values_list("title", flat=True)[:400])
    suggestions.extend(recipe_titles)

    # user profiles
    userprofile = User.objects.all().only("first_name", "last_name")

    user_profiles = [profile.get_full_name() for profile in userprofile]

    suggestions.extend(user_profiles)

    # user history
    history = []

    if request.user.is_authenticated:
        history = list(BlogHistory.objects.filter(user=request.user).select_related("blog_post").values_list("blog_post__title", flat=True)[:10])

    autocomplete_context = {
        "autocomplete_list_json": json.dumps(
            {
                "suggestions": suggestions,
                "history": history,
            }
        )
    }

    cache.set(AUTOCOMPLETE_CACHE_KEY, autocomplete_context, AUTOCOMPLETE_CACHE_TTL)

    return autocomplete_context


def message_notifications(request):
    if not request.user.is_authenticated:
        return {"notifications": []}
    cache_key = f"notifications_{request.user.id}"
    notifications = cache.get(cache_key)
    if notifications is None:
        notifications = Notification.objects.filter(recipient=request.user).order_by("-timestamp")[:10]
        cache.set(cache_key, notifications, timeout=300)
    return {"notifications": notifications}


def most_searched_recipes(request):
    if request.user.is_authenticated:
        global_rankings = (
            searchedRecipesRanking.objects.values("recipe").annotate(total_searches=Count("user")).order_by("-total_searches")[:5]
        )  # Top 10
        recipes_rankings = (
            post.objects.filter(id__in=[ranking["recipe"] for ranking in global_rankings])
            .annotate(search_count=Count("recipe_rankings"))
            .order_by("-search_count", "-hit_count_generic__hits", "-date_post")
        )
    else:
        recipes_rankings = []
    return {"recipes_rankings": recipes_rankings}


def todays_date(request):
    todays_date = datetime.date.today()
    return {"todays_date": todays_date}


def guest_user_context(request):
    guest_user = request.session.get("guest_user")
    is_guest = bool(guest_user and not request.user.is_authenticated)

    return {"guest_user": guest_user, "is_guest": is_guest}


def recipes(request):
    all_recipes = post.objects.filter().all()

    return {"all_recipes": all_recipes}
