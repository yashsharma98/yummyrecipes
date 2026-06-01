from django.conf import settings
from django.http import JsonResponse
from django.template.defaultfilters import striptags
from google import genai


def summarize_content(request):
    if request.method == "POST":
        content = request.POST.get("content", "")

        try:
            post_content = striptags(content)

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[f"Summarize the recipe instructions {post_content}"],
            )

            return JsonResponse({"summarizedContent": response.text})

        except Exception:
            return JsonResponse({"error": "Unable to process the request. Try again later"})

    return JsonResponse({"error": "Invalid request method"}, status=400)
