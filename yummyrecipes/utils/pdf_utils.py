from io import BytesIO
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.http import (
    HttpResponse,
)
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from xhtml2pdf import pisa

from ..models import (
    photo,
    post,
)

# @login_required(login_url="login")
# def customer_render_pdf_view(request, feed, pk, *args, **kwargs):
#     recipes = get_object_or_404(post, title=feed)
#     recipe_images = photo.objects.filter(feed=recipes)

#     recipe_title = recipes.title or "recipe"
#     safe_filename = recipe_title.replace(" ", "_")
#     filename = f"{safe_filename}.pdf"

#     if settings.ENVIRONMENT == "True":
#         if recipe_images.exists():
#             pdf_recipe_image_url = recipe_images.first().image.url
#         else:
#             pdf_recipe_image_url = None

#         if recipes.author and recipes.author.profile.profile_img:
#             profile_image_path = recipes.author.profile.profile_img.url
#             pdf_profile_image_url = urljoin("file://", profile_image_path)
#         else:
#             pdf_profile_image_url = None
#     else:
#         if recipe_images.exists():
#             pdf_recipe_image_url = recipe_images.first().image.path
#         else:
#             pdf_recipe_image_url = None

#         if recipes.author and recipes.author.profile.profile_img:
#             profile_image_path = recipes.author.profile.profile_img.path
#             pdf_profile_image_url = urljoin("file://", profile_image_path)
#         else:
#             pdf_profile_image_url = None

#     nutrition_info = None

#     query = recipes.title

#     if query:
#         try:
#             api_url = "https://api.api-ninjas.com/v1/nutrition?query="
#             api_request = requests.get(api_url + query, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
#             api_data = json.loads(api_request.content)

#             if api_request.status_code == 200:
#                 nutrition_info = api_data

#         except Exception:
#             nutrition_info = "Error"

#     html_content = render_to_string(
#         "yummyrecipes/viewpdf.html",
#         {
#             "recipes": recipes,
#             "pdf_recipe_image_url": pdf_recipe_image_url,
#             "nutrition_info": nutrition_info,
#             "pdf_profile_image_url": pdf_profile_image_url,
#         },
#     )

#     css = finders.find("yummyrecipes/pdf_recipe.css")

#     options = {"enable-local-file-access": None}

#     pdf = pdfkit.from_string(html_content, False, options=options, css=[css])

#     response = HttpResponse(pdf, content_type="application/pdf")
#     response["Content-Disposition"] = f'inline; filename="{filename}"'

#     return response


@login_required(login_url="login")
def customer_render_pdf_view(request, feed, pk, *args, **kwargs):
    recipes = get_object_or_404(post, title=feed)
    recipe_images = photo.objects.filter(feed=recipes)

    recipe_title = recipes.title or "recipe"
    safe_filename = recipe_title.replace(" ", "_")
    filename = f"{safe_filename}.pdf"

    from ..ml.predictor import predict_recipe_time

    # using ml model to pred the recipe timings
    pred_time = predict_recipe_time(recipes)

    # Handle images (local path vs URL depending on ENVIRONMENT)
    if settings.ENVIRONMENT == "True":
        pdf_recipe_image_url = recipe_images.first().image.url if recipe_images.exists() else None
        pdf_profile_image_url = (
            urljoin("file://", recipes.author.profile.profile_img.url) if recipes.author and recipes.author.profile.profile_img else None
        )
    else:
        pdf_recipe_image_url = recipe_images.first().image.path if recipe_images.exists() else None
        pdf_profile_image_url = (
            urljoin("file://", recipes.author.profile.profile_img.path) if recipes.author and recipes.author.profile.profile_img else None
        )

    # Nutrition API
    nutrition_info = None
    query = recipes.title
    if query:
        try:
            api_url = "https://api.api-ninjas.com/v1/nutrition?query="
            api_request = requests.get(api_url + query, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
            if api_request.status_code == 200:
                nutrition_info = api_request.json()
        except Exception:
            nutrition_info = "Error"

    # Render HTML template
    html_content = render_to_string(
        "yummyrecipes/viewpdf.html",
        {
            "recipes": recipes,
            "pdf_recipe_image_url": pdf_recipe_image_url,
            "nutrition_info": nutrition_info,
            "pdf_profile_image_url": pdf_profile_image_url,
            "pred_time": pred_time,
        },
    )

    # Add CSS (inline injection since xhtml2pdf has weaker CSS support)
    css_path = finders.find("yummyrecipes/pdf_recipe.css")
    if css_path:
        with open(css_path, "r") as css_file:
            css_content = f"<style>{css_file.read()}</style>"
        html_content = css_content + html_content

    # Generate PDF
    result = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=result, encoding="utf-8")

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    # Return response
    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def shopping_list_pdf(request, title, pk, *args, **kwargs):
    recipe_object = get_object_or_404(post, pk=pk)

    recipe_ingredients = recipe_object.ingredients

    html_content = render_to_string("yummyrecipes/shopping_list.html", {"recipe_object": recipe_object, "recipe_ingredients": recipe_ingredients})

    file_name = f"{recipe_object.title}.pdf"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{file_name}"'

    pisa_status = pisa.CreatePDF(
        html_content,
        dest=response,
    )

    if pisa_status.err:
        return HttpResponse("Error generating PDF", status=500)

    return response
