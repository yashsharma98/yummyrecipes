import re
from dataclasses import dataclass
from typing import Optional

recipe_filters = {
    "type": ["breakfast", "lunch", "dinner", "snack"],
    "cuisine": ["indian", "italian", "american"],
    "difficulty": ["easy", "medium", "hard"],
}

categories = {
    "non-veg": ["non veg", "nonveg", "non-veg"],
    "veg": ["veg", "vegetarian"],
}

page_urls = {
    "home": "/",
    "profile": "/profile/",
    "dashboard": "/dashboard/",
    "explore": "/explore/",
    "timeline": "/timeline/",
    "trending": "/trending/",
    "credits": "/credits/",
    "feedback": "/feedback/",
    "history": "/history/",
    "favourites": "/favourites/",
    "liked recipes": "/liked_recipes/",
    "disliked recipes": "/disliked_recipes/",
    "views": "/total_views/",
    "network": "/network/",
    "appearance": "/appearance/",
    "account settings": "/account_settings/",
    "update profile": "/updateprofile/",
    "new recipe": "/newrecipe/",
    "kitchenai": "/kitchenai/",
}


def extract_navigation(query: str):
    if not query:
        return None

    val = query.lower().strip()

    if len(val.split()) > 2:
        return None

    if val in page_urls:
        return page_urls[val]

    for key, url in page_urls.items():
        if key.startswith(val):
            return url

    return None


def extract_filters(query):
    found = {}
    val = query.lower()

    # veg / non-veg category
    if re.search(r"\bnon\s*-?\s*veg\b", val):
        found["category"] = "non-veg"
    elif re.search(r"\bveg\b", val):
        found["category"] = "veg"

    # other remainin filters
    for field, values in recipe_filters.items():
        if field == "category":
            continue

        for q in values:
            if re.search(rf"\b{re.escape(q)}\b", val):
                found[field] = q
                break

    return found


@dataclass
class QueryOperators:
    operator: str
    value: int | None = None
    min_value: int | None = None
    max_value: int | None = None


def extract_servings_intent(query: str) -> Optional[QueryOperators]:
    val = query.lower()

    range_match = re.search(r"(serves?|for)\s*(\d+)\s*(to|-)\s*(\d+)", val)

    if range_match:
        return QueryOperators(
            operator="between",
            min_value=int(range_match.group(2)),
            max_value=int(range_match.group(4)),
        )

    patterns = [
        # For exact match
        (r"(for|serves?)\s*(\d+)", "="),
        (r"(at\s+least|minimum|min)\s*(\d+)", ">="),
        (r"(at\s+most|up\s+to|maximum|max)\s*(\d+)", "<="),
        (r"(more\s+than|greater\s+than)\s*(\d+)", ">"),
        (r"(less\s+than)\s*(\d+)", "<"),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, val)
        if match:
            return QueryOperators(operator=operator, value=int(match.group(2)))

    return None


def extract_timing_intent(query: str) -> Optional[QueryOperators]:
    val = query.lower()

    range_match = re.search(r"(\d+)\s*(to|-)\s*(\d+)\s*(min|mins|minutes)", val)

    if range_match:
        return QueryOperators(
            operator="between",
            min_value=int(range_match.group(1)),
            max_value=int(range_match.group(3)),
        )

    patterns = [
        (r"(under|less\s+than)\s*(\d+)\s*(min|mins|minutes)?", "<"),
        (r"(at\s+most|up\s+to|max|maximum)\s*(\d+)\s*(min|mins|minutes)?", "<="),
        (r"(at\s+least|min|minimum)\s*(\d+)\s*(min|mins|minutes)?", ">="),
        (r"(more\s+than|greater\s+than)\s*(\d+)\s*(min|mins|minutes)?", ">"),
        (r"(\d+)\s*(min|mins|minutes)", "="),
    ]

    for pattern, operator in patterns:
        match = re.search(pattern, val)
        if match:
            return QueryOperators(operator=operator, value=int(match.group(2)))

    return None


@dataclass
class DifficultyIntent:
    operator: str
    level: str


def extract_difficulty_intent(query: str) -> Optional[DifficultyIntent]:
    val = query.lower()

    levels = ["easy", "medium", "hard"]

    for lvl in levels:
        if f"at least {lvl}" in val or f"minimum {lvl}" in val:
            return DifficultyIntent(operator=">=", level=lvl)

    for lvl in levels:
        if f"at most {lvl}" in val or f"no {lvl}" in val:
            return DifficultyIntent(operator="<=", level=lvl)

    for lvl in levels:
        if lvl in val:
            return DifficultyIntent(operator="=", level=lvl)

    return None


INTENT_SYNONYMS = {
    "quick": {
        "timing": ("<=", 10),
    },
    "fast": {
        "timing": ("<=", 25),
    },
    "party": {
        "type": "Evening Snack recipes",
    },
    "snacks": {
        "type": "Evening Snack recipes",
    },
    "kids": {
        "difficulty": ("<=", "easy"),
    },
    "light": {
        "difficulty": ("<=", "medium"),
    },
}


def apply_synonym_intents(query, filters, timing, difficulty):
    val = query.lower()

    for keyword, intent in INTENT_SYNONYMS.items():
        if not re.search(rf"\b{keyword}\b", val):
            continue

        if "timing" in intent and timing is None:
            op, value = intent["timing"]
            timing = QueryOperators(operator=op, value=value)

        if "type" in intent and "type" not in filters:
            filters["type"] = intent["type"]

        if "difficulty" in intent and difficulty is None:
            op, level = intent["difficulty"]
            difficulty = DifficultyIntent(operator=op, level=level)

    return filters, timing, difficulty
