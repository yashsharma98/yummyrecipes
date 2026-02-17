from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, F

from ..models import post


@shared_task
def update_trending_posts():
    trending = (
        post.objects.select_related("author")
        .annotate(
            total_hits=F("hit_count_generic__hits"),
            total_likes=Count("likes", distinct=True),
        )
        .order_by("-total_hits", "-total_likes", "-date_post")
        .only("id", "title", "author", "hit_count_generic__hits", "date_post")[:20]
    )

    cache.set("trending_posts", list(trending.values()), timeout=60 * 10)
    return f"{trending.count()} posts cached"
