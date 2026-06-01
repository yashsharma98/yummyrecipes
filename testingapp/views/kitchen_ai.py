import base64
import json
import re
from io import BytesIO

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import (
    JsonResponse,
)
from django.shortcuts import render
from google import genai
from PIL import Image

from ..forms import (
    AIRecipeGenerationForm,
)


def cloudflare_image_generation(prompt):
    url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/leonardo/phoenix-1.0"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "prompt": prompt,
            "width": 512,
            "height": 512,
        },
        timeout=120,
    )
    response.raise_for_status()

    return Image.open(BytesIO(response.content))


def generate_recipe_with_ai_image(request):
    form = AIRecipeGenerationForm()

    initial_query = ""

    if request.method == "GET" and "query" in request.GET:
        initial_query = request.GET.get("query", "").strip()

        form = AIRecipeGenerationForm(initial={"title": initial_query})

    if request.method == "POST" and request.POST.get("img_type") == "recipeimage":
        regenerate = request.POST.get("regenerate") == "1"

        try:
            image_generation_form = AIRecipeGenerationForm(request.POST)

            if image_generation_form.is_valid():
                title = image_generation_form.cleaned_data["title"]

                cache_key = f"generated_recipe_{title.lower().strip()}"

                if not regenerate:
                    cached_data = cache.get(cache_key)

                    if cached_data:
                        return JsonResponse(cached_data)

                # STEP 1
                # Generate recipe JSON
                generated_recipe = generate_recipe_content(title)

                # STEP 2
                # Extract image description
                image_description = generated_recipe.get(
                    "image_description",
                    title,
                )

                # STEP 3
                # Generate image prompt
                prompt = f"""
                    Generate a professional food photography.

                    {image_description}

                    Authentic regional preparation.
                    Traditional serving style.
                    Real cooked food.
                    Natural lighting.
                    Visible ingredients.
                    Accurate colors and textures.
                    Food magazine quality.

                    No illustration.
                    No cartoon.
                    No painting.
                    No CGI.
                    No 3D render.
                    No text.
                    No watermark.
                """

                image_url = None

                try:
                    image = cloudflare_image_generation(prompt)

                    buffer = BytesIO()

                    image.convert("RGB").save(
                        buffer,
                        format="JPEG",
                        quality=70,
                        optimize=True,
                    )

                    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

                    image_url = f"data:image/jpeg;base64,{base64_image}"

                except Exception:
                    image_url = None

                set_cache = {
                    "recipe_image_url": image_url,
                    "generated_recipe": generated_recipe,
                    "image_description": image_description,
                }

                cache.set(
                    cache_key,
                    set_cache,
                    timeout=7200,
                )

                return JsonResponse(set_cache)

        except Exception as e:
            return JsonResponse({"error": str(e)})

    return render(request, "testingapp/generate_recipe.html",{"form": form, "initial_query": initial_query})


def generate_recipe_content(title):
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[
            f"""
                Generate a realistic recipe for "{title}".

                Return ONLY valid JSON.

                Schema:

                {{
                    "title": "",
                    "image_description": "",
                    "nutrition": {{
                        "calories": "",
                        "protein": "",
                        "fat": "",
                        "carbohydrates": "",
                        "fiber": "",
                        "sugar": "",
                        "sodium": ""
                    }},
                    "details": {{
                        "prep_time": "",
                        "cook_time": "",
                        "servings": "",
                        "category": "",
                        "difficulty": "",
                        "cuisine": "",
                        "best_time": ""
                    }},
                    "ingredients": [],
                    "instructions": []
                }}

                Rules:

                - image_description should visually describe the final cooked dish.
                - Mention visible ingredients.
                - Mention plating.
                - Mention garnish.
                - Mention colors.
                - Mention texture.
                - Mention serving vessel.
                - Mention camera angle.
                - Use realistic values.
                - Return JSON only.
                - Do not use markdown.
                - Do not use ```json.
                - Do not include explanations.
                """
        ],
    )

    generated_recipe = response.text.strip()

    generated_recipe = re.sub(
        r"^```json|^```|```$",
        "",
        generated_recipe,
        flags=re.MULTILINE,
    ).strip()

    return json.loads(generated_recipe)
