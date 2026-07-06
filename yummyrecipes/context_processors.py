import datetime
import json

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from notifications.models import Notification

from .models import BlogHistory, post, searchedRecipesRanking


def search_autocomplete_data(request):
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

    # Categories
    suggestions.extend(f"{category} recipes" for category in categories)

    suggestions.extend(f"{category} {meal} recipes" for category in categories for meal in meal_types)

    # Cuisine
    suggestions.extend(f"{cuisine} cuisine recipes" for cuisine in cuisines)

    suggestions.extend(f"{cuisine} {difficulty} recipes" for cuisine in cuisines for difficulty in difficulties)

    # Difficulty
    suggestions.extend(f"{difficulty} {meal} recipes" for difficulty in difficulties for meal in meal_types)

    # Timing
    for phrase in timing_phrases:
        suggestions.append(phrase)

        suggestions.extend(f"{phrase} for {meal}" for meal in meal_types)

    # Recipe titles
    recipe_titles = post.objects.order_by("title").values_list("title", flat=True)[:500]

    suggestions.extend(recipe_titles)

    # User full names
    user_names = [user.get_full_name().strip() for user in User.objects.only("first_name", "last_name") if user.get_full_name().strip()]

    suggestions.extend(user_names)

    # Remove duplicates while preserving order
    suggestions = list(dict.fromkeys(suggestions))

    # User history
    history = []

    if request.user.is_authenticated:
        history = list(BlogHistory.objects.filter(user=request.user).select_related("blog_post").values_list("blog_post__title", flat=True)[:10])

    return {
        "autocomplete_list_json": json.dumps(
            {
                "suggestions": suggestions,
                "history": history,
            }
        )
    }


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
