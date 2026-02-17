from .home_utils import get_meal_counts


def build_meal_context(meal_posts=None, meal_type=None):
    counts = get_meal_counts()
    context = {
        "brkfst_count": counts["Breakfast"],
        "lnch_count": counts["Lunch"],
        "evesnack_count": counts["Evening Snack"],
        "dnr_count": counts["Dinner"],
    }

    if meal_posts is not None:
        context["meal_posts"] = meal_posts
    if meal_type is not None:
        context["meal_type"] = meal_type

    return context
