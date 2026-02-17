import openai
from django.conf import settings
from django.http import (
    JsonResponse,
)
from django.template.defaultfilters import striptags
from django.utils.html import strip_tags
from google import genai

openai.api_key = settings.OPENAI_API_KEY


def summarize_text(text):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",
            prompt=text,
            max_tokens=150,
            temperature=0.4,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
        )
        return response.choices[0].text.strip()
    except Exception:
        return text


def summarize_content(request):
    if request.method == "POST":
        content = request.POST.get("content", "")

        # If OpenAI API is available
        if settings.OPENAI_API_KEY:
            try:
                summarized_content, status_code = summarize_text(content)

                # uncomment below line if not using typing simulation in the template
                # safe_summarized_content = SafeString(summarized_content)

                safe_summarized_content = strip_tags(summarized_content)

                return JsonResponse(
                    {
                        "summarizedContent": safe_summarized_content,
                        "status_code": status_code,
                    }
                )

            except Exception as e:
                return JsonResponse({"error": str(e)})

        # Else use GEMINI API
        else:
            try:
                post_content = striptags(content)

                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[f"Summarize the recipe instructions {post_content}"],
                )

                return JsonResponse({"summarizedContent": response.text})

            except Exception as e:
                return JsonResponse({"error": str(e)})

    return JsonResponse({"error": "Invalid request method"}, status=400)


# def summarize_text(text):
#     api_key = settings.OPENAI_API_KEY
#     api_endpoint = "https://api.openai.com/v1/engines/gpt-3.5-turbo-instruct/completions"

#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {api_key}",
#     }

#     data = {
#         "prompt": text,
#         "max_tokens": 100,
#     }

#     response = requests.post(api_endpoint, json=data, headers=headers)

#     if response.status_code == 200:
#         return response.json()["choices"][0]["text"], response.status_code
#     else:
#         return None, response.status_code
