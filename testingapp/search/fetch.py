from django.contrib.auth.models import User
from django.db.models import Q
from pgvector.django import CosineDistance

from ..models import BlogHistory, post


def fetch_recipes_exact(query):
    return post.objects.filter(title__iexact=query)


def fetch_recipes_partial(query):
    return post.objects.filter(title__icontains=query)


def fetch_recipes_filtered(filters, timing=None, servings=None, difficulty=None):
    if not filters and not timing and not servings:
        return post.objects.none()

    recipe_val = post.objects.all()

    for field, value in filters.items():
        if field not in {"type", "cuisine", "category", "difficulty"}:
            continue

        if field == "category":
            recipe_val = recipe_val.filter(category__iexact=value)

        elif field == "difficulty":
            recipe_val = recipe_val.filter(difficulty__iexact=value)

        elif field == "type":
            recipe_val = recipe_val.filter(type__iexact=value)

        elif field == "cuisine":
            recipe_val = recipe_val.filter(cuisine__iexact=value)

    if timing:
        if timing.operator == "between":
            recipe_val = recipe_val.filter(timing__gte=timing.min_value, timing__lte=timing.max_value)
        else:
            val = timing.value
            op = timing.operator

            if op == "=":
                recipe_val = recipe_val.filter(timing=val)
            elif op == "<":
                recipe_val = recipe_val.filter(timing__lt=val)
            elif op == "<=":
                recipe_val = recipe_val.filter(timing__lte=val)
            elif op == ">":
                recipe_val = recipe_val.filter(timing__gt=val)
            elif op == ">=":
                recipe_val = recipe_val.filter(timing__gte=val)

    if servings:
        if servings.operator == "between":
            recipe_val = recipe_val.filter(servings__gte=servings.min_value, servings__lte=servings.max_value)

        else:
            op = servings.operator
            val = servings.value
            if op == "=":
                recipe_val = recipe_val.filter(servings=val)
            elif op == ">=":
                recipe_val = recipe_val.filter(servings__gte=val)
            elif op == "<=":
                recipe_val = recipe_val.filter(servings__lte=val)
            elif op == ">":
                recipe_val = recipe_val.filter(servings__gt=val)
            elif op == "<":
                recipe_val = recipe_val.filter(servings__lt=val)

    recipe_difficulty = {
        "easy": 1,
        "medium": 2,
        "hard": 3,
    }

    if difficulty:
        target = recipe_difficulty[difficulty.level]

        if difficulty.operator == "=":
            recipe_val = recipe_val.filter(difficulty=difficulty.level)

        elif difficulty.operator == ">=":
            allowed = [k for k, v in recipe_difficulty.items() if v >= target]
            recipe_val = recipe_val.filter(difficulty__in=allowed)

        elif difficulty.operator == "<=":
            allowed = [k for k, v in recipe_difficulty.items() if v <= target]
            recipe_val = recipe_val.filter(difficulty__in=allowed)

    return recipe_val


def fetch_users(query):
    return User.objects.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query))


def fetch_history(user, query):
    if not user.is_authenticated:
        return BlogHistory.objects.none()

    return BlogHistory.objects.filter(user=user, blog_post__title__icontains=query)


def fetch_recipes_semantic(query, limit=8, max_distance=0.35):
    """
    Semantic similarity using pgvector.
    Lower distance = more similar.
    """
    # preventing heavy startup load
    from .semantic_cache import cached_query_embedding

    query_embedding = cached_query_embedding(query)

    recipe_val = (
        post.objects.exclude(embedding__isnull=True)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lte=max_distance)
        .order_by("distance")[:limit]
    )

    return recipe_val
