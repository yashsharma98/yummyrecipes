from ..models import post
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
    filters = extract_filters(query)
    timing = extract_timing_intent(query)
    servings = extract_servings_intent(query)
    difficulty = extract_difficulty_intent(query)
    navigation = extract_navigation(query)

    exact_recipes = fetch_recipes_exact(query)
    filtered_recipes = fetch_recipes_filtered(filters, timing, servings, difficulty)
    partial_recipes = fetch_recipes_partial(query)

    filters, timing, difficulty = apply_synonym_intents(query, filters, timing, difficulty)

    query_type = classify_query(query)
    semantic_recipes = post.objects.none()

    if query_type == descriptive_query:
        semantic_recipes = fetch_recipes_semantic(query)

    elif query_type == exact_query and not exact_recipes.exists():
        semantic_recipes = fetch_recipes_semantic(query)

    no_db_results = not exact_recipes.exists() and not filtered_recipes.exists() and not partial_recipes.exists() and not semantic_recipes.exists()

    show_google = False
    show_kitchen_ai = False

    if no_db_results:
        show_google = True

    show_kitchen_ai = query_type == descriptive_query or no_db_results

    return {
        "navigation": navigation,
        "exact_recipes": exact_recipes,
        "filtered_recipes": filtered_recipes,
        "partial_recipes": partial_recipes,
        "semantic_recipes": semantic_recipes,
        "users": fetch_users(query),
        "history": fetch_history(request.user, query),
        "show_google": show_google,
        "show_kitchen_ai": show_kitchen_ai,
    }
