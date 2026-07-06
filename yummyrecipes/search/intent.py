from .extractors import extract_filters, extract_servings_intent, extract_timing_intent

descriptive = {"healthy", "quick", "easy", "best", "good", "tasty", "food", "dish", "recipe", "something"}
exact_query = "exact"
filter_query = "filter"
descriptive_query = "descriptive"


class QueryIntent:
    def __init__(
        self,
        wants_navigation=False,
        wants_recipes=True,
        wants_people=False,
        has_filters=False,
        has_timing=False,
        is_descriptive=False,
    ):
        self.wants_navigation = wants_navigation
        self.wants_recipes = wants_recipes
        self.wants_people = wants_people
        self.has_filters = has_filters
        self.has_timing = has_timing
        self.is_descriptive = is_descriptive


def is_descriptive_query(query):
    words = set(query.lower().split())
    return len(words) >= 4 and bool(words & descriptive)


def classify_query(query):
    """
    Classifies query into:
    exact: recipe name search
    filter: structured intent (veg, non-veg, time, servings, etc.)
    descriptive: like long recipe name or title search
    """

    filters = extract_filters(query)
    timing = extract_timing_intent(query)
    servings = extract_servings_intent(query)

    if is_descriptive_query(query):
        return descriptive_query

    if filters or timing or servings:
        return filter_query

    return exact_query
