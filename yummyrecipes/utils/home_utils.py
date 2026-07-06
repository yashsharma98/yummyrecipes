import datetime
from random import choice

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from hitcount.models import HitCount

from ..models import post


def get_meal_posts(hour=None):
    hour = hour or datetime.datetime.now().hour
    meal_map = [(4, "Dinner"), (12, "Breakfast"), (17, "Lunch"), (19, "Evening Snack"), (24, "Dinner")]

    for limit, meal in meal_map:
        if hour < limit:
            posts = list(post.objects.filter(type=meal).order_by("-hit_count_generic__hits", "-date_post")[:12])
            return posts, f"{meal} recipes"
    return [], ""


def get_popular_recipes():
    cached = cache.get("popular_recipes")
    if cached:
        return cached

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
        return fallback

    posts = list(post.objects.filter(pk__in=post_ids))
    cache.set("popular_recipes", posts, 3600)
    return posts


def get_trending_recipes():
    return cache.get_or_set("trending_recipes", lambda: list(post.objects.order_by("-hit_count_generic__hits")[:20]), 1800)


def get_random_post():
    pks = cache.get("all_post_pks")
    if not pks:
        pks = list(post.objects.values_list("pk", flat=True))
        cache.set("all_post_pks", pks, 600)
    return post.objects.get(pk=choice(pks)) if pks else None


def get_meal_counts():
    counts = cache.get("meal_counts")
    if counts:
        return counts

    counts = {
        "Breakfast": post.objects.filter(type="Breakfast").count(),
        "Lunch": post.objects.filter(type="Lunch").count(),
        "Evening Snack": post.objects.filter(type="Evening Snack").count(),
        "Dinner": post.objects.filter(type="Dinner").count(),
    }
    cache.set("meal_counts", counts, 1800)
    return counts


def recipe_recommendations(title, cosine_sim, indices, posts_df):
    indx = indices[title]
    sim_scores = list(enumerate(cosine_sim[indx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[:10]
    post_indices = [i[0] for i in sim_scores]
    return posts_df.iloc[post_indices]


@login_required
def add_to_favorites(request, id):
    blog = get_object_or_404(post, id=id)

    if blog.favourites.filter(id=request.user.id).exists():
        blog.favourites.remove(request.user)
        action = "remove"
    else:
        blog.favourites.add(request.user)
        action = "add"

    return JsonResponse(
        {
            "action": action,
            "post_id": id,
        }
    )
