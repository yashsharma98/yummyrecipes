import json
import urllib.request

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from google import genai


@shared_task
def fetch_weather_and_cache(location):
    location = location.strip().lower()

    api_key = settings.OPENWEATHERMAP_API_KEY
    weather_cache_key = f"weather_data_{location}"
    lock_key = f"weather_fetching_{location}"
    # recipe_cache_key = f"suggested_recipes_{location}"

    try:
        res = urllib.request.urlopen(f"http://api.openweathermap.org/data/2.5/weather?q={location}&mode=json&units=metric&appid={api_key}").read()
        json_data = json.loads(res)

        weather_data = {
            "temp": int(json_data["main"]["temp"]),
            "des": str(json_data["weather"][0]["main"]),
            "location": str(json_data["name"]),
            "wind_speed": int(json_data["wind"]["speed"]),
            "feels_like": int(json_data["main"]["feels_like"]),
            "min": int(json_data["main"]["temp_min"]),
            "max": int(json_data["main"]["temp_max"]),
            "icon": str(json_data["weather"][0]["icon"]),
            "humidity": str(json_data["main"]["humidity"]),
        }

        # summary via gemini
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # prompt = f"Summarize {weather_data['location']} weather: {weather_data['des']} at {weather_data['temp']}°C under 5 lines"

        prompt = (
            f"Summarize the weather in {weather_data['location']}. "
            f"It is {weather_data['des']} with a temperature of {weather_data['temp']} degrees Celsius. "
            "Use plain text only. "
            "Do not use symbols, markdown, bullet points, asterisks, or formatting. "
            "Write no more than 3 short sentences."
        )
        response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=[prompt])

        weather_data["summary"] = response.text if response else "Weather summary unavailable."

        # Cache weather for 2 hours
        cache.set(weather_cache_key, weather_data, timeout=7200)

        # Recipe suggestions
        # recipe_data, gemini_response = suggest_recipes(weather_data)

        # cache.set(recipe_cache_key, (recipe_data, gemini_response), timeout=7200)

        return True

    except Exception:
        return False

    finally:
        cache.delete(lock_key)


# Enable other scheduler code in settings.py
# @shared_task
# def refresh_all_user_weather():
#     from ..models import UserLocation

# locations = (
#     UserLocation.objects
#     .filter(user__last_login__gte=active_since)
#     .exclude(location="")
#     .values_list("location", flat=True)
#     .distinct()
# )

#     for location in locations:
#         fetch_weather_and_cache.delay(location)


# def suggest_recipes(weather_data):
#     cache_key = f"suggested_recipes_{weather_data['location']}_{weather_data['temp']}_{weather_data['des']}"
#     cached_data = cache.get(cache_key)

#     if cached_data:
#         return cached_data

#     try:
#         conn = psycopg2.connect(
#             host=settings.DB_HOST,
#             port=settings.DB_PORT,
#             dbname=settings.DB_NAME,
#             user=settings.DB_USER,
#             password=settings.DB_PASSWORD,
#             sslmode=settings.DB_SSLMODE,
#         )

#         cursor = conn.cursor()
#         cursor.execute("""
#             SELECT p.id, p.title, COALESCE(ph.image, '')
#             FROM testingapp_post p
#             LEFT JOIN testingapp_photo ph ON ph.feed_id = p.id
#             GROUP BY p.id, p.title, ph.image;
#         """)
#         recipes_data = cursor.fetchall()
#         conn.close()

#         # Creating a list of from recipes_data tuple for prompt
#         recipes_list = "\n".join([f"- {title} (ID: {pk})" for pk, title, image in recipes_data])

#         prompt = f"""
#             Weather in {weather_data["location"]}: Temperature {weather_data["temp"]}°C, Condition: {weather_data["des"]}.
#             Available Recipes:
#             {recipes_list}
#             Suggest the best recipes for this weather. Avoid using '**' for formatting. Also provide a very short explanation (7-10 words).
#         """

#         client = genai.Client(api_key=settings.GEMINI_API_KEY)

#         response = client.models.generate_content(model="gemini-2.0-flash", contents=[f"{prompt}"])

#         gemini_response = response.text

#         matches = re.findall(r"([\w\s]+)\s+\(ID:\s*(\d+)\):\s*(.*)", gemini_response)
#         suggested_recipes = {match[1]: match[2] for match in matches}

#         recipes_dict = {str(pk): {"title": title, "image": image} for pk, title, image in recipes_data}

#         suggested_recipes_data = [
#             {
#                 "id": pk,
#                 "title": recipes_dict[pk]["title"],
#                 "image": default_storage.url(recipes_dict[pk]["image"]) if recipes_dict[pk]["image"] else "",
#                 "description": suggested_recipes.get(pk),
#             }
#             for pk in suggested_recipes
#             if pk in recipes_dict
#         ]
#         if suggested_recipes_data:
#             cache.set(cache_key, (suggested_recipes_data, gemini_response), timeout=3600)
#         return suggested_recipes_data, gemini_response

#     except Exception:
#         return []
