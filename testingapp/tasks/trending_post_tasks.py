from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, F
from django.db.models.functions import Coalesce

from ..models import post


@shared_task
def update_trending_posts():
    trending = (
        post.objects.annotate(
            total_hits=Coalesce(F("hit_count_generic__hits"), 0),
            total_likes=Count("likes", distinct=True),
        )
        .order_by("-total_hits", "-total_likes", "-date_post")
        .values("id", "title")[:20]
    )

    trending_list = list(trending)
    cache.set("trending_posts", trending_list, timeout=60 * 10)

    return f"{len(trending_list)} posts cached"
