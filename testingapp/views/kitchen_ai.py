import base64
from io import BytesIO

import openai
from django.conf import settings
from django.core.cache import cache
from django.http import (
    JsonResponse,
)
from django.shortcuts import render
from google import genai
from google.genai import types
from PIL import Image

from ..forms import (
    AIRecipeGenerationForm,
)


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
                # Get the title from the image generation form
                title = image_generation_form.cleaned_data["title"]

                cache_key = f"generated_recipe_{title.lower().strip()}"
                cached_data = cache.get(cache_key)

                # Return cached data and handling regeneration of recipe
                if not regenerate:
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        return JsonResponse(cached_data)

                # if OpenAI API is available then generate both recipe and its image
                if openai.api_key:
                    openai.api_key = settings.OPENAI_API_KEY

                    # Generate an image based on the user's input
                    response = openai.Image.create(prompt=title, n=1, size="256x256")

                    try:
                        # Download the generated image
                        recipe_image_url = response.data[0].url
                    except (AttributeError, KeyError):
                        # Handle the case where the response structure doesn't provide a direct URL
                        recipe_image_url = None

                    # Call the second function to generate the recipe
                    generated_recipe = generate_recipe_content(title)

                    formatted_generated_recipe = generated_recipe.replace("\n", "<br>")

                    set_cache = {
                        "recipe_image_url": recipe_image_url,
                        "generated_recipe": formatted_generated_recipe,
                    }

                    cache.set(cache_key, set_cache, timeout=7200)
                    return JsonResponse(set_cache)

                    # if recipe_image_url:
                    #     return JsonResponse({"recipe_image_url": recipe_image_url,"generated_recipe": formatted_generated_recipe})

                # Else use Gemini API to generate both recipe and its image
                else:
                    image_url = None

                    try:
                        client = genai.Client(api_key=settings.GEMINI_API_KEY)

                        response = client.models.generate_content(
                            model="gemini-2.5-flash-image",
                            contents=[f"Generate an image for {title}"],
                            config=types.GenerateContentConfig(
                                response_modalities=["Image"],
                            ),
                        )

                        for part in response.candidates[0].content.parts:
                            if part.inline_data is not None:
                                # Convert binary data to base64 string for URL response
                                image_data = part.inline_data.data
                                image = Image.open(BytesIO(image_data))

                                # Save to a temporary buffer
                                buffered = BytesIO()
                                image.save(buffered, format="PNG")

                                # Convert image to base64 string
                                base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                image_url = f"data:image/png;base64,{base64_image}"
                                break

                    except Exception:
                        image_url = None

                    # Generate recipe
                    generated_recipe = generate_recipe_content(title)
                    formatted_generated_recipe = generated_recipe.replace("\n", "")

                    set_cache = {
                        "recipe_image_url": image_url,
                        "generated_recipe": formatted_generated_recipe,
                    }

                    cache.set(cache_key, set_cache, timeout=7200)
                    return JsonResponse(set_cache)

                    # return JsonResponse({"recipe_image_url": image_url,"generated_recipe": formatted_generated_recipe})

                    # generated_recipe = generate_recipe(title)

                    # formatted_generated_recipe = generated_recipe.replace('\n', '')
                    # return JsonResponse({"recipe_image_url": None,"generated_recipe": formatted_generated_recipe})

        except Exception as e:
            error = str(e)
            return JsonResponse({"error": error})

    form = AIRecipeGenerationForm()
    return render(
        request,
        "testingapp/generate_recipe.html",
        {"form": form, "initial_query": initial_query},
    )


def generate_recipe_content(title):
    try:
        # Generate recipe using OpenAI API
        # recipe_prompt = f"Generate a recipe for {title}."
        # recipe_response = openai.Completion.create(
        #     engine="gpt-3.5-turbo-instruct",
        #     prompt=recipe_prompt,
        #     max_tokens=50,
        #     temperature=0.7,
        #     n=1,
        # )

        # generated_recipe = recipe_response.choices[0].text.strip()

        # return generated_recipe

        # Generating recipe using Gemini API
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                f"""Generate a recipe for {title} with detailed nutritional information in grams only, not for ingredients. 
                    Start with the recipe title '{title}' in an <h1> tag at the top. Below the title, wrap two tables
                    in a <div> with class 'generated-recipe-table-container'. The first table is for nutritional information limited to the most 
                    important nutrients: Calories, Protein, Fat, Carbohydrates, Fiber, Sugar, and Sodium, with no inline styling 
                    attributes like border or other styles; use only <table>, <tr>, <th>, and <td> tags. The second table is for 
                    the following details: Prep Time, Cook Time, Servings, Category (veg or non-veg), Difficulty, Cuisine, and 
                    Best Time to Consume (use one or two words); use only <table>, <tr>, <th>, and <td> tags with no inline styling 
                    attributes. Below the tables, include an <h3> tag for 'Ingredients' followed by numbered bullet points with 
                    <ol> and <li> tags for the ingredient list. Then, include an <h3> tag for 'Instructions' followed by numbered 
                    bullet points with <ol> and <li> tags for the instruction list. Use only periods (.) in the bullet points and 
                    avoid any special characters. Provide the output as pure HTML without code block markers like ``` or ''' or 
                    the word 'html'. At the end, add an appropriate cooking-related closing message with an emoji relevant to the 
                    recipe, separated by some vertical space using single <br> tag.
                """
            ],
        )

        generated_recipe = response.text
        if "```" in generated_recipe:
            generated_recipe = generated_recipe.replace("```html", "").replace("```", "").strip()

        # generated_recipe = response.text
        return generated_recipe

    except Exception as e:
        error = str(e)
        return JsonResponse({"error": error})
