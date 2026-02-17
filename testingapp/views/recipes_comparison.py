import json

import requests
from django.conf import settings
from django.contrib import messages
from django.http import (
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    CreditSpentHistory,
    photo,
    post,
)
from ..utils.recipes_helper import get_recipe_nutrition_widget


def compare_recipes(request, pk):
    titles = post.objects.all()
    recipe1 = get_object_or_404(post, pk=pk)
    photo1 = get_object_or_404(photo, feed=recipe1)

    if request.method == "POST":
        recipe_id1 = request.POST.get("recipe1")
        recipe_id2 = request.POST.get("recipe2")

        if recipe_id1 and recipe_id2:
            return redirect("compare_view", recipe_id1=recipe_id1, recipe_id2=recipe_id2)

    # getting nutrition info from api
    query = recipe1.title

    nutrition_widget1 = get_recipe_nutrition_widget(recipe1.ingredients)

    nutrition_info_error, nutrition_info = None, None

    if query:
        try:
            api_url = "https://api.api-ninjas.com/v1/nutrition?query="
            api_request = requests.get(api_url + query, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
            api_data = json.loads(api_request.content)

            if api_request.status_code == 200:
                nutrition_info = api_data
            else:
                nutrition_info_error = "Error occurred"

        except ConnectionError:
            nutrition_info_error = "Could not connect to Api"

        except Exception:
            nutrition_info_error = "Error"

    # return redirect('recipe_compare_form')
    return render(
        request,
        "testingapp/compare_recipes.html",
        {
            "titles": titles,
            "pk": pk,
            "recipe1": recipe1,
            "photo1": photo1,
            "nutrition_info": nutrition_info,
            "nutrition_info_error": nutrition_info_error,
            "nutrition_widget1": nutrition_widget1,
        },
    )


def compare_recipes_new(request):
    if request.method == "POST":
        recipe_id1 = request.POST.get("recipe1")
        recipe_id2 = request.POST.get("recipe2")

        if recipe_id1 and recipe_id2:
            return redirect("compare_view", recipe_id1=recipe_id1, recipe_id2=recipe_id2)

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def compare_view(request, recipe_id1, recipe_id2):
    recipe1 = get_object_or_404(post, pk=recipe_id1)
    recipe2 = get_object_or_404(post, pk=recipe_id2)

    photo1 = get_object_or_404(photo, feed=recipe1)
    photo2 = get_object_or_404(photo, feed=recipe2)

    titles = post.objects.all()

    user = request.user

    if user.is_authenticated and not request.session.get(f"viewed_post_{recipe_id2}", False):
        if user.profile.credits >= 1:
            user.profile.credits -= 1
            user.profile.credits_spent += 1

            CreditSpentHistory.objects.create(user=user, recipename=recipe2, amount=1)

            user.profile.save()
            request.session[f"viewed_post_{recipe_id2}"] = True
        else:
            error_msg = "Not enough credits to compare recipe"
            messages.error(request, error_msg, extra_tags="no-more-credits")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    nutrition_widget1 = get_recipe_nutrition_widget(recipe1.ingredients)
    nutrition_widget2 = get_recipe_nutrition_widget(recipe2.ingredients)

    # getting nutrition info from api
    query1 = recipe1.title
    query2 = recipe2.title

    nutrition_info_error1, nutrition_info1 = None, None
    nutrition_info_error2, nutrition_info2 = None, None

    if query1:
        try:
            api_url = "https://api.api-ninjas.com/v1/nutrition?query="
            api_request = requests.get(api_url + query1, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
            api_data = json.loads(api_request.content)

            if api_request.status_code == 200:
                nutrition_info1 = api_data
            else:
                nutrition_info_error1 = "Error occurred"

        except ConnectionError:
            nutrition_info_error1 = "Could not connect to Api"

        except Exception:
            nutrition_info_error1 = "Error"

    if query2:
        try:
            api_url = "https://api.api-ninjas.com/v1/nutrition?query="
            api_request = requests.get(api_url + query2, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
            api_data = json.loads(api_request.content)

            if api_request.status_code == 200:
                nutrition_info2 = api_data
            else:
                nutrition_info_error2 = "Error occurred"

        except ConnectionError:
            nutrition_info_error2 = "Could not connect to Api"

        except Exception:
            nutrition_info_error2 = "Error"

    context = {
        "recipe1": recipe1,
        "recipe2": recipe2,
        "photo1": photo1,
        "photo2": photo2,
        "titles": titles,
        "nutrition_info1": nutrition_info1,
        "nutrition_info_error1": nutrition_info_error1,
        "nutrition_info2": nutrition_info2,
        "nutrition_info_error2": nutrition_info_error2,
        "nutrition_widget1": nutrition_widget1,
        "nutrition_widget2": nutrition_widget2,
    }
    return render(request, "testingapp/compare_recipes.html", context)
