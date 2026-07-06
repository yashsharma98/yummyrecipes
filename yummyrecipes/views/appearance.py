import json
from datetime import datetime, time

from coloraide import Color
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    JsonResponse,
)
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from google import genai

from ..decorators import login_or_guest_required
from ..models import (
    UserProfile,
)

DAY_THEME = {
  "primary_color": "#F97316",
  "secondary_color": "#FFFBF5",
  "tertiary_color": "#1F2937",
  "active_link_color": "#EA580C",
  "hover_color": "#B1D3B9",
  "neutral_primary": "#618764",
  "neutral_secondary": "#E5E7EB"
}


def set_day_theme(profile):
    profile.primary_color = DAY_THEME["primary_color"]
    profile.secondary_color = DAY_THEME["secondary_color"]
    profile.tertiary_color = DAY_THEME["tertiary_color"]
    profile.active_link_color = DAY_THEME["active_link_color"]
    profile.hover_color = DAY_THEME["hover_color"]
    profile.neutral_primary = DAY_THEME["neutral_primary"]
    profile.neutral_secondary = DAY_THEME["neutral_secondary"]


@require_POST
@login_or_guest_required
def apply_day_theme(request):
    if request.guest_active:
        return JsonResponse({"success": False, "message": "Guest support later"}, status=400)

    profile = request.user.userprofile
    set_day_theme(profile)

    profile.theme = "day"
    profile.schedule_enabled = False
    profile.save()

    return JsonResponse({"success": True, "theme": "day", "colors": DAY_THEME, "schedule_enabled": False, "schedule_mode": "off"})


NIGHT_THEME = {
    "primary_color": "#39393a",
    "secondary_color": "#252422",
    "tertiary_color": "#f5f5dc",
    "active_link_color": "#829cbc",
    "hover_color": "#6d6a75",
    "neutral_primary": "#0077b6",
    "neutral_secondary": "#5c6b73",
}


def set_night_theme(profile):
    profile.primary_color = NIGHT_THEME["primary_color"]
    profile.secondary_color = NIGHT_THEME["secondary_color"]
    profile.tertiary_color = NIGHT_THEME["tertiary_color"]
    profile.active_link_color = NIGHT_THEME["active_link_color"]
    profile.hover_color = NIGHT_THEME["hover_color"]
    profile.neutral_primary = NIGHT_THEME["neutral_primary"]
    profile.neutral_secondary = NIGHT_THEME["neutral_secondary"]


@require_POST
@login_or_guest_required
def apply_night_theme(request):
    if request.guest_active:
        return JsonResponse({"success": False, "message": "Guest support later"}, status=400)

    profile = request.user.userprofile

    set_night_theme(profile)

    profile.theme = "night"
    profile.schedule_enabled = False
    profile.save()

    return JsonResponse({"success": True, "theme": "night", "colors": NIGHT_THEME, "schedule_enabled": False, "schedule_mode": "off"})


def get_active_theme(profile):
    """
    Returns:
    day
    night
    blur
    """

    if not profile.schedule_enabled:
        return profile.theme

    now = datetime.now().time()

    # AUTO MODE
    if profile.schedule_mode == "auto":
        if now >= time(18, 0) or now < time(6, 0):
            return "night"

        return "day"

    # CUSTOM MODE

    start = profile.night_start
    end = profile.night_end

    if not start or not end:
        return "day"

    # Cross midnight
    if start > end:
        is_night = now >= start or now < end
    else:
        is_night = start <= now < end

    return "night" if is_night else "day"


@login_required
@require_POST
def save_schedule(request):
    profile = request.user.userprofile

    mode = request.POST.get("mode")

    if mode == "off":
        profile.schedule_enabled = False
        profile.schedule_mode = "off"
        profile.theme = "day"

        set_day_theme(profile)

    elif mode == "auto":
        profile.schedule_enabled = True
        profile.schedule_mode = "auto"

        active_theme = get_active_theme(profile)

        if active_theme == "night":
            set_night_theme(profile)
        else:
            set_day_theme(profile)

    elif mode == "custom":
        start = datetime.strptime(request.POST["night_start"], "%H:%M").time()

        end = datetime.strptime(request.POST["night_end"], "%H:%M").time()

        profile.schedule_enabled = True
        profile.schedule_mode = "custom"
        profile.night_start = start
        profile.night_end = end

        active_theme = get_active_theme(profile)

        if active_theme == "night":
            set_night_theme(profile)
        else:
            set_day_theme(profile)

    else:
        return JsonResponse({"success": False, "message": "Invalid mode"}, status=400)

    profile.save()

    active_theme = get_active_theme(profile)

    return JsonResponse(
        {
            "success": True,
            "active_theme": active_theme,
            "schedule_enabled": profile.schedule_enabled,
            "schedule_mode": profile.schedule_mode,
            "colors": NIGHT_THEME if active_theme == "night" else DAY_THEME,
        }
    )


def adjust_oklch(hex_color, *, lightness=0.0, chroma=0.0, hue=0.0):
    color = Color(hex_color).convert("oklch")

    color["l"] = max(0, min(1, color["l"] + lightness))
    color["c"] = max(0, color["c"] + chroma)
    color["h"] = (color["h"] + hue) % 360

    return color.convert("srgb").fit().to_string(hex=True).upper()


# def generate_custom_theme(primary, secondary, tertiary):
#     return {
#         "primary_color": primary,
#         "secondary_color": secondary,
#         "tertiary_color": tertiary,
#         "neutral_primary": adjust_oklch(primary, lightness=-0.15, chroma=-0.02, hue=120),
#         "neutral_secondary": adjust_oklch(primary, lightness=0.2, chroma=-0.1, hue=90),
#         # from Secondary
#         "active_link_color": adjust_oklch(secondary, lightness=-0.08, chroma=0.04),
#         "hover_color": adjust_oklch(secondary, lightness=0.06, chroma=0.02),
#     }


def luminance(hex_color):
    """
    Returns perceived luminance (0-255).
    Lower = darker.
    """
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return (0.299 * r) + (0.587 * g) + (0.114 * b)


def generate_custom_theme(primary, secondary, tertiary):
    lum = luminance(secondary)

    if lum < 20:
        # Pure / near black
        lightness = 0.22

    elif lum < 50:
        # Very dark
        lightness = 0.16

    elif lum < 100:
        # Dark
        lightness = 0.10

    elif lum < 170:
        # Medium
        lightness = 0.04

    else:
        # Light backgrounds
        lightness = -0.06

    neutral_secondary = adjust_oklch(
        primary,
        lightness=lightness,
        chroma=-0.08,
        hue=20,
    )

    return {
        "primary_color": primary,
        "secondary_color": secondary,
        "tertiary_color": tertiary,
        # Neutral accent derived from primary
        "neutral_primary": adjust_oklch(
            primary,
            lightness=-0.15,
            chroma=-0.02,
            hue=120,
        ),
        # Neutral surface derived from secondary
        "neutral_secondary": neutral_secondary,
        # Interactive colors derived from secondary
        "active_link_color": adjust_oklch(
            secondary,
            lightness=-0.08,
            chroma=0.04,
        ),
        "hover_color": adjust_oklch(secondary, lightness=0.06, chroma=0.02),
    }


@login_required
@require_POST
def custom_theme(request):
    profile = request.user.userprofile

    primary = request.POST.get("primary_color")

    secondary = request.POST.get("secondary_color")

    tertiary = request.POST.get("tertiary_color")

    theme = generate_custom_theme(
        primary,
        secondary,
        tertiary,
    )

    profile.primary_color = theme["primary_color"]
    profile.secondary_color = theme["secondary_color"]
    profile.tertiary_color = theme["tertiary_color"]

    profile.neutral_primary = theme["neutral_primary"]
    profile.neutral_secondary = theme["neutral_secondary"]

    profile.active_link_color = theme["active_link_color"]
    profile.hover_color = theme["hover_color"]

    profile.theme = "custom"
    profile.schedule_enabled = False

    profile.save(
        update_fields=[
            "theme",
            "schedule_enabled",
            "primary_color",
            "secondary_color",
            "tertiary_color",
            "neutral_primary",
            "neutral_secondary",
            "active_link_color",
            "hover_color",
        ]
    )

    return JsonResponse(
        {
            "success": True,
            "theme": "custom",
            "schedule_enabled": False,
            "schedule_mode": "off",
            "colors": theme,
        }
    )


@login_required
@require_POST
def generate_ai_theme(request):
    prompt = request.POST.get("theme_description", "").strip()

    if not prompt:
        return JsonResponse({"success": False, "error": "Theme description is required."}, status=400)

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=f"""
                You are an expert UI/UX designer specializing in modern web application color systems.

                Generate EXACTLY FOUR unique professional themes for a recipe/social web application.

                Return ONLY valid JSON.

                Each theme MUST contain these fields:

                name
                primary_color
                secondary_color
                tertiary_color
                neutral_primary
                neutral_secondary
                active_link_color
                hover_color

                Every color MUST be a valid HEX color in the format:

                #RRGGBB

                --------------------------------------------------
                COLOR ROLES
                --------------------------------------------------

                primary_color
                - Primary action color.
                - Used for buttons, primary actions, links, badges and highlights.
                - Should be clean, modern and elegant.
                - Prefer a medium-light color rather than a highly saturated one.
                - Avoid neon, overly vibrant or overly punchy colors.
                - Should be bright enough to stand out against the background but not dominate the interface.
                - Should remain readable with white text.
                - Think of a refined accent color rather than a bold brand color.

                secondary_color
                - Main application background.
                - Used as the page background.
                - Can be light OR dark depending on the theme.
                - Must be comfortable for reading.
                - Avoid extremely saturated backgrounds.

                tertiary_color
                - Primary text color.
                - Used for almost all text.
                - MUST have excellent contrast with secondary_color.
                - If secondary_color is light, tertiary_color MUST be dark.
                - If secondary_color is dark, tertiary_color MUST be light.
                - Text readability is the highest priority.

                neutral_primary
                - Used for cards, side panels, elevated containers and featured sections.
                - This should be the most visually striking surface color in the theme.
                - Rich, bold and premium.
                - High contrast against secondary_color.
                - Should immediately pop from the background.
                - May use a different hue from primary_color if it creates a stronger design.
                - Avoid dull or gray-looking colors.
                - This color should have more visual impact than primary_color.

                neutral_secondary
                - Used for subtle backgrounds, input fields and hover surfaces.
                - Soft muted surface color.
                - Slightly darker than a pastel.
                - Should have noticeable contrast against secondary_color while remaining subtle.
                - Low saturation.
                - Can have a different hue than primary_color.
                - Should feel calm and balanced.
                - Must be lighter than neutral_primary but clearly darker than the page background.

                active_link_color
                - Used as the background color of the currently selected navigation item.
                - Should relate to primary_color.
                - Slightly richer than primary_color.
                - Must remain visually distinct from primary_color.

                hover_color
                - Used for hover states.
                - Soft highlight color.
                - Slightly stronger than neutral_secondary.
                - Never brighter than primary_color.

                --------------------------------------------------
                DESIGN RULES
                --------------------------------------------------

                - Create visually balanced themes.
                - Colors should feel modern and premium.
                - Avoid muddy or dull palettes.
                - Avoid neon colors.
                - Maintain proper visual hierarchy.
                - The palette should work well for a professional website.
                - Every theme should have a different personality.
                - Use complementary or analogous colors where appropriate.
                - Prefer harmonious palettes over random colors.

                --------------------------------------------------
                VERIFY BEFORE RETURNING
                --------------------------------------------------

                For EACH theme verify that:

                - tertiary_color has excellent contrast with secondary_color.

                - primary_color is clearly visible on secondary_color.

                - primary_color is lighter than neutral_primary.

                - neutral_primary has significantly higher contrast against secondary_color than primary_color.

                - primary_color and neutral_primary are clearly distinguishable at first glance.

                - neutral_primary does not appear to be simply a darker version of primary_color.

                - neutral_secondary is softer than neutral_primary.

                - active_link_color is different from primary_color.

                - hover_color is appropriate for hover states.

                --------------------------------------------------
                RETURN FORMAT
                --------------------------------------------------

                Return ONLY this JSON format.
                {{
                "themes": [
                    {{
                        "name": "",
                        "primary_color": "",
                        "secondary_color": "",
                        "tertiary_color": "",
                        "neutral_primary": "",
                        "neutral_secondary": "",
                        "active_link_color": "",
                        "hover_color": ""
                    }},
                    {{
                        "name": "",
                        "primary_color": "",
                        "secondary_color": "",
                        "tertiary_color": "",
                        "neutral_primary": "",
                        "neutral_secondary": "",
                        "active_link_color": "",
                        "hover_color": ""
                    }},
                    {{
                        "name": "",
                        "primary_color": "",
                        "secondary_color": "",
                        "tertiary_color": "",
                        "neutral_primary": "",
                        "neutral_secondary": "",
                        "active_link_color": "",
                        "hover_color": ""
                    }},
                    {{
                        "name": "",
                        "primary_color": "",
                        "secondary_color": "",
                        "tertiary_color": "",
                        "neutral_primary": "",
                        "neutral_secondary": "",
                        "active_link_color": "",
                        "hover_color": ""
                    }}
                ]
                }}

                User request:

                {prompt}
            """,
    )

    text = response.text.strip()

    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        data = json.loads(text)

    except Exception:
        return JsonResponse({"success": False, "error": "Gemini returned invalid JSON."}, status=500)

    return JsonResponse({"success": True, "themes": data["themes"]})


@login_required
@require_POST
def apply_ai_theme(request):
    profile = request.user.userprofile

    fields = [
        "primary_color",
        "secondary_color",
        "tertiary_color",
        "neutral_primary",
        "neutral_secondary",
        "active_link_color",
        "hover_color",
    ]

    colors = {}

    for field in fields:
        value = request.POST.get(field)
        setattr(profile, field, value)
        colors[field] = value

    profile.theme = "ai"
    profile.schedule_enabled = False
    # profile.theme_name = request.POST.get("theme_name", "")
    profile.theme_name = request.POST.get("theme_name") or "AI Theme"
    profile.save()

    return JsonResponse(
        {"success": True, "theme": "ai", "schedule_enabled": False, "schedule_mode": "off", "theme_name": profile.theme_name, **colors}
    )


@never_cache
# @login_required(login_url='login')
@login_or_guest_required
def appearance(request):
    if not request.guest_active:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        profile = request.user.userprofile

        appearance_state = {
            "appearance": ("schedule" if profile.schedule_enabled else get_active_theme(profile)),
            "themeStudio": ("ai" if profile.theme == "ai" else "custom"),
            "showCurrentAI": (profile.theme == "ai"),
        }

        return render(
            request,
            "yummyrecipes/appearance.html",
            {
                "user_profile": user_profile,
                "active_theme": get_active_theme(profile),
                "schedule_active": profile.schedule_enabled,
                "theme_studio_tab": ("ai" if profile.theme == "ai" else "custom"),
                "appearance_state": appearance_state,
            },
        )
    else:
        if request.method == "POST":
            guest_data = request.session.get("guest_user", {})

            guest_uuid = guest_data.get("uuid")
            guest_name = guest_data.get("name")
            guest_email = guest_data.get("email")

            guest_data["uuid"] = guest_uuid
            guest_data["name"] = guest_name
            guest_data["email"] = guest_email

            request.session["guest_user"] = guest_data
            request.session.modified = True

        return render(request, "yummyrecipes/appearance.html", {"active_theme": user_profile.theme})
