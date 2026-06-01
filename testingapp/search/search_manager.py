from django.contrib.auth.models import User

from ..models import BlogHistory, post
from .extractors import (
    apply_synonym_intents,
    extract_difficulty_intent,
    extract_filters,
    extract_navigation,
    extract_servings_intent,
    extract_timing_intent,
)
from .fetch import (
    fetch_history,
    fetch_recipes_exact,
    fetch_recipes_filtered,
    fetch_recipes_partial,
    fetch_recipes_semantic,
    fetch_users,
)
from .intent import classify_query, descriptive_query, exact_query


def search_flow(query, request):
    query = query.strip()

    # page navigation
    navigation = extract_navigation(query)

    if navigation:
        return {
            "navigation": navigation,
            "exact_recipes": post.objects.none(),
            "filtered_recipes": post.objects.none(),
            "partial_recipes": post.objects.none(),
            "semantic_recipes": post.objects.none(),
            "users": User.objects.none(),
            "history": BlogHistory.objects.none(),
            "show_google": False,
            "show_kitchen_ai": False,
        }

    # query intents
    filters = extract_filters(query)
    timing = extract_timing_intent(query)
    servings = extract_servings_intent(query)
    difficulty = extract_difficulty_intent(query)

    filters, timing, difficulty = apply_synonym_intents(query, filters, timing, difficulty)

    query_type = classify_query(query)

    exact_recipes = fetch_recipes_exact(query)
    filtered_recipes = fetch_recipes_filtered(filters, timing, servings, difficulty)
    partial_recipes = fetch_recipes_partial(query)

    # Only run user search for short queries
    users = User.objects.none()
    if len(query.split()) <= 3:
        users = fetch_users(query)

    # history search if user is logged in
    history = BlogHistory.objects.none()
    if request.user.is_authenticated and len(query.split()) <= 4:
        history = fetch_history(request.user, query)

    combined_recipes = exact_recipes.union(filtered_recipes, partial_recipes)

    has_recipes = combined_recipes.exists()
    has_users = users.exists()

    # semantic search recipes
    semantic_recipes = post.objects.none()

    if query_type == descriptive_query:
        semantic_recipes = fetch_recipes_semantic(query)

    elif query_type == exact_query and not (has_recipes or has_users):
        semantic_recipes = fetch_recipes_semantic(query)

    has_semantic = semantic_recipes.exists() if semantic_recipes else False

    # fallbacks
    no_db_results = not (has_recipes or has_semantic or has_users)

    show_google = no_db_results
    show_kitchen_ai = query_type == descriptive_query or no_db_results

    return {
        "navigation": navigation,
        "exact_recipes": exact_recipes,
        "filtered_recipes": filtered_recipes,
        "partial_recipes": partial_recipes,
        "semantic_recipes": semantic_recipes,
        "users": users,
        "history": history,
        "show_google": show_google,
        "show_kitchen_ai": show_kitchen_ai,
    }
