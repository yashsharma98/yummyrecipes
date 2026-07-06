import numpy as np
from celery import shared_task
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from hitcount.models import HitCount

from ..models import UserTasteProfile, post, profile


@shared_task
def update_popular_recipes_cache():
    today = timezone.now()
    start_week = today - timezone.timedelta(days=today.weekday())
    end_week = start_week + timezone.timedelta(days=6)

    hit_counts = (
        HitCount.objects.filter(hit__created__range=[start_week, end_week])
        .values("object_pk")
        .annotate(hit_count=Count("pk"))
        .order_by("-hit_count")[:5]
    )

    post_ids = [item["object_pk"] for item in hit_counts]

    if not post_ids:
        fallback = list(post.objects.order_by("-hit_count_generic__hits")[:5])
        cache.set("popular_recipes", fallback, 3600)
        return

    posts = list(post.objects.filter(pk__in=post_ids))
    cache.set("popular_recipes", posts, 3600)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5})
def update_user_taste_profile(self, user_id):
    user = User.objects.get(id=user_id)
    user_profile = profile.objects.get(user=user)

    vectors = []
    weights = []

    liked_recipes = post.objects.filter(likes=user_profile, embedding__isnull=False).only("embedding")
    for recipe in liked_recipes:
        vectors.append(recipe.embedding)
        weights.append(1.0)

    fav_recipes = post.objects.filter(favourites=user, embedding__isnull=False).only("embedding")
    for recipe in fav_recipes:
        vectors.append(recipe.embedding)
        weights.append(1.2)

    viewed_recipes = post.objects.filter(bloghistory__user=user, embedding__isnull=False).distinct().only("embedding")[:20]
    for recipe in viewed_recipes:
        vectors.append(recipe.embedding)
        weights.append(0.4)

    searched_recipes = post.objects.filter(recipe_rankings__user=user, embedding__isnull=False).only("embedding")
    for recipe in searched_recipes:
        vectors.append(recipe.embedding)
        weights.append(0.6)

    disliked_recipes = post.objects.filter(dislikes=user_profile, embedding__isnull=False).only("embedding")
    for recipe in disliked_recipes:
        vectors.append(recipe.embedding)
        weights.append(-1.0)

    if not vectors or sum(weights) == 0:
        return "Insufficient signal to build taste profile"

    vectors = np.array(vectors, dtype=float)
    weights = np.array(weights)
    taste_vector = np.average(vectors, axis=0, weights=weights)

    UserTasteProfile.objects.update_or_create(
        user=user,
        defaults={"taste_vector": taste_vector.tolist()},
    )

    return "User taste profile updated"


@shared_task
def refresh_all_user_tastes():
    user_ids = list(User.objects.values_list("id", flat=True))
    for user_id in user_ids:
        update_user_taste_profile.delay(user_id)
