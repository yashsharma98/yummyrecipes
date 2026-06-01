import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import JsonResponse
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_protect
from google import genai
from requests.exceptions import RequestException

from ..models import post

API_KEY = settings.SPOONACULAR_API_KEY


def clean_ingredients(html_ingredients):
    soup = BeautifulSoup(html_ingredients, "html.parser")
    cleaned_ingredients = soup.get_text(separator="\n").strip()
    ingredients_list = cleaned_ingredients.splitlines()

    formatted_ingredients = "\n".join([ingredient.strip() for ingredient in ingredients_list if ingredient.strip()])

    return formatted_ingredients


def get_recipe_nutrition_widget(ingredients):
    cleaned_ingredients = clean_ingredients(ingredients)

    url = "https://api.spoonacular.com/recipes/visualizeNutrition"
    data = {"ingredientList": cleaned_ingredients, "apiKey": API_KEY, "defaultCss": True}

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()

        return response.text

    except RequestException:
        return "Information is not unavailable"


def get_recommendations(recipe_id, num_recommendations=50):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    recipe = post.objects.get(id=recipe_id)

    recipes = list(post.objects.all())

    descriptions = [recipe.content for recipe in recipes]
    ingredients = [recipe.ingredients for recipe in recipes]

    combined_features = [f"{desc} {ingre}" for desc, ingre in zip(descriptions, ingredients)]

    tfidf_vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = tfidf_vectorizer.fit_transform(combined_features)

    cosine_similarities = cosine_similarity(tfidf_matrix, tfidf_matrix)

    recipe_index = recipes.index(recipe)

    similarity_scores = cosine_similarities[recipe_index]
    similar_indices = similarity_scores.argsort()[-(num_recommendations + 1) : -1][::-1]

    recommended_recipes = [recipes[int(index)] for index in similar_indices]

    return recommended_recipes


@csrf_protect  # Remove if using {% csrf_token %}
def translate_content(request):
    if request.method == "POST":
        post_content = request.POST.get("post_content", "")
        stripped_content = strip_tags(post_content)

        if settings.GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[f"Translate the following instruction into Hindi: {stripped_content}"],
                )

                return JsonResponse({"translated_text": response.text.strip()})

            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)
