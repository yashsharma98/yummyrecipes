from django.db.models import F
from pgvector.django import CosineDistance

from testingapp.models import RecipeRecommendationHistory

from ..models import UserTasteProfile, post, profile

# Recommending recipe to user based on these factors
""" 
taste = liked vectors + favorite vectors + viewed vectors - disliked vectors

like = 1, favourit = 1.2, view = 0.4, dislike = -1, search = 0.6
"""


# when user has no taste profile
def default_recommendations(user, limit):
    recipes = (
        post.objects.filter(embedding__isnull=False)
        .select_related("author", "author__profile")
        .annotate(hit_count_value=F("hit_count_generic__hits"))
        .order_by("-date_post")[:limit]
    )

    return list(recipes)


def recommendations(user, recipes):
    """
    Logs which recipes were shown to the user.
    Avoids duplicates per session window.
    """

    if not user or not user.is_authenticated:
        return

    logs = []

    for recipe in recipes:
        logs.append(
            RecipeRecommendationHistory(
                user=user,
                recipe=recipe,
                score=getattr(recipe, "score", None),
            )
        )

    RecipeRecommendationHistory.objects.bulk_create(logs)


def personalized_recommendations(user, limit=20):
    try:
        taste_profile = UserTasteProfile.objects.get(user=user)
        user_vector = taste_profile.taste_vector
    except UserTasteProfile.DoesNotExist:
        return list(default_recommendations(user, limit))

    user_profile = profile.objects.get(user=user)

    # recipes = post.objects.filter(embedding__isnull=False).select_related("author", "author__profile").prefetch_related("likes", "dislikes")
    recipes = (
        post.objects.filter(embedding__isnull=False)
        .select_related("author", "author__profile")
        .prefetch_related("photo_set", "likes", "dislikes")
        .annotate(
            score=CosineDistance("embedding", user_vector),
            hit_count_value=F("hit_count_generic__hits"),
        )
    )

    if user_profile.preference_category and user_profile.preference_category != "Select":
        recipes = recipes.filter(category__icontains=user_profile.preference_category)

    if user_profile.preference_cuisine and user_profile.preference_cuisine != "Select":
        recipes = recipes.filter(cuisine__icontains=user_profile.preference_cuisine)

    if user_profile.preference_type and user_profile.preference_type != "Select":
        recipes = recipes.filter(type__icontains=user_profile.preference_type)

    recipes = recipes.order_by("score")[:limit]

    recipes = list(recipes)

    recommendations(user, recipes)

    return recipes
