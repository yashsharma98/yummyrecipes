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
    qs = (
        post.objects.filter(embedding__isnull=False)
        .select_related("author", "author__profile")
        .annotate(hit_count_value=F("hit_count_generic__hits"))
        .order_by("-date_post")[:limit]
    )

    return list(qs)


def _log_recommendations(user, recipes):
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

    # qs = post.objects.filter(embedding__isnull=False).select_related("author", "author__profile").prefetch_related("likes", "dislikes")
    qs = (
        post.objects.filter(embedding__isnull=False)
        .select_related("author", "author__profile")
        .prefetch_related("photo_set", "likes", "dislikes")
        .annotate(
            score=CosineDistance("embedding", user_vector),
            hit_count_value=F("hit_count_generic__hits"),
        )
    )

    if user_profile.preference_category and user_profile.preference_category != "Select":
        qs = qs.filter(category__icontains=user_profile.preference_category)

    if user_profile.preference_cuisine and user_profile.preference_cuisine != "Select":
        qs = qs.filter(cuisine__icontains=user_profile.preference_cuisine)

    if user_profile.preference_type and user_profile.preference_type != "Select":
        qs = qs.filter(type__icontains=user_profile.preference_type)

    qs = qs.order_by("score")[:limit]

    recipes = list(qs)

    _log_recommendations(user, recipes)

    return recipes
