import pandas as pd

from .model_loader import load_models


def predict_recipe_time(post):
    if not post.title or not post.ingredients:
        return None

    try:
        prep_pipeline, cook_pipeline = load_models()

        X = pd.DataFrame(
            {
                "text": [f"{post.title} {post.ingredients}"],
                "Cuisine": [post.cuisine or "Unknown"],
                "Course": [post.type or "Unknown"],
                "Diet": [post.category or "Unknown"],
                "Servings": [post.servings or 2],
                "ingredient_count": [len(post.ingredients.split(","))],
                "title_length": [len(post.title)],
            }
        )

        prep_time = float(prep_pipeline.predict(X)[0])
        cook_time = float(cook_pipeline.predict(X)[0])

        prep_time = max(2, min(prep_time, 120))
        cook_time = max(2, min(cook_time, 240))

        total_time = int(round(prep_time + cook_time))

        return {
            "prep": int(round(prep_time)),
            "cook": int(round(cook_time)),
            "total": total_time,
        }

    except Exception:
        return None
