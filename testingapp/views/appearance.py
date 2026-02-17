import re

from django.conf import settings
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from google import genai

from ..decorators import login_or_guest_required
from ..forms import (
    AIcolorCodeGenerationForm,
    UseColorFromImageForm,
)
from ..models import (
    UserProfile,
)


def hex_to_rgba(hex_color, alpha=0.2):
    hex_color = hex_color.strip().lstrip("#")

    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    if len(hex_color) != 6:
        return f"rgba(255,255,255,{alpha})"

    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
    except ValueError:
        return f"rgba(255,255,255,{alpha})"

    return f"rgba({r},{g},{b},{alpha})"


def dynamic_css(request):
    if not request.guest_active:
        user = request.user
        user_profile = UserProfile.objects.get(user=user)

        if request.method == "POST":
            if request.POST.get("transparent_form") == "blurform":
                theme_name = request.POST.get("transparent_theme")
                user_profile.theme = theme_name
                user_profile.save()

                return JsonResponse({"status": "ok", "theme": theme_name})
                # return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

        if user_profile.theme == "transparent_theme":
            template_name = "testingapp/frosted.css"
        else:
            template_name = "testingapp/dynamic.css"

        css = render_to_string(
            template_name,
            {
                "user": user,
                "primary_rgba": hex_to_rgba(user_profile.primary_color, 0.3),
                "secondary_rgba": hex_to_rgba(user_profile.secondary_color, 0.4),
                "tertiary_rgba": hex_to_rgba(user_profile.tertiary_color, 0.2),
                "active_link_rgba": hex_to_rgba(user_profile.active_link_color, 0.7),
                "hover_rgba": hex_to_rgba(user_profile.hover_color, 0.4),
                "neutral_primary_rgba": hex_to_rgba(user_profile.neutral_primary, 0.4),
                "neutral_secondary_rgba": hex_to_rgba(user_profile.neutral_secondary, 0.4),
                "primary_rgba_2": hex_to_rgba(user_profile.primary_color, 0.8),
                "tertiary_rgba_2": hex_to_rgba(user_profile.tertiary_color, 0.3),
                "neutral_primary_rgba_2": hex_to_rgba(user_profile.neutral_primary, 0.4),
                "neutral_secondary_rgba_2": hex_to_rgba(user_profile.neutral_secondary, 0.95),
            },
        )
        return HttpResponse(css, content_type="text/css")

    else:
        session_theme = request.session.get("guest_user", {})
        user_uuid = session_theme.get("uuid")

        primary = session_theme.get("primary_color", "#DBCBBD")
        secondary = session_theme.get("secondary_color", "#F0ECE3")
        tertiary = session_theme.get("tertiary_color", "#221e20")
        active_link = session_theme.get("active_link_color", "#9F8772")
        hover = session_theme.get("hover_color", "#9C938B")
        neutral_primary = session_theme.get("neutral_primary", "#DFBB9D")
        neutral_secondary = session_theme.get("neutral_secondary", "#DBD7CB")

        css = render_to_string(
            "testingapp/guest.css",
            {
                "uuid": user_uuid,
                "primary_color": primary,
                "secondary_color": secondary,
                "tertiary_color": tertiary,
                "active_link_color": active_link,
                "hover_color": hover,
                "neutral_primary": neutral_primary,
                "neutral_secondary": neutral_secondary,
                "primary_rgba": hex_to_rgba(primary, 0.3),
                "secondary_rgba": hex_to_rgba(secondary, 0.4),
                "tertiary_rgba": hex_to_rgba(tertiary, 0.2),
                "active_link_rgba": hex_to_rgba(active_link, 0.7),
                "hover_rgba": hex_to_rgba(hover, 0.4),
                "neutral_primary_rgba": hex_to_rgba(neutral_primary, 0.4),
                "neutral_secondary_rgba": hex_to_rgba(neutral_secondary, 0.95),
                "primary_rgba_2": hex_to_rgba(primary, 0.8),
                "tertiary_rgba_2": hex_to_rgba(tertiary, 0.3),
                "neutral_primary_rgba_2": hex_to_rgba(neutral_primary, 0.4),
                "neutral_secondary_rgba_2": hex_to_rgba(neutral_secondary, 0.95),
            },
        )

        response = HttpResponse(css, content_type="text/css")
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


# Sending RGBA colors to basetheme
def get_transparent_rgba_colors(request):
    user = request.user
    profile = UserProfile.objects.get(user=user)

    data = {
        "primary_rgba": hex_to_rgba(profile.primary_color, 0.3),
        "secondary_rgba": hex_to_rgba(profile.secondary_color, 0.4),
        "tertiary_rgba": hex_to_rgba(profile.tertiary_color, 0.2),
        "active_link_rgba": hex_to_rgba(profile.active_link_color, 0.7),
        "hover_rgba": hex_to_rgba(profile.hover_color, 0.4),
        "neutral_primary_rgba": hex_to_rgba(profile.neutral_primary, 0.4),
        "neutral_secondary_rgba": hex_to_rgba(profile.neutral_secondary, 0.4),
        "primary_rgba_2": hex_to_rgba(profile.primary_color, 0.8),
        "tertiary_rgba_2": hex_to_rgba(profile.tertiary_color, 0.3),
        "neutral_primary_rgba_2": hex_to_rgba(profile.neutral_primary, 0.4),
        "neutral_secondary_rgba_2": hex_to_rgba(profile.neutral_secondary, 0.95),
    }
    return JsonResponse(data)


def extract_hex_codes(text):
    return re.findall(r"#[a-fA-F0-9]{6}", text)


@never_cache
# @login_required(login_url='login')
@login_or_guest_required
def appearance(request):
    if not request.guest_active:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        if request.method == "POST":
            if request.POST.get("form_type") == "colorform":
                primary_color = request.POST.get("primary_color")
                theme = request.POST.get("custom_primary_color")
                user_profile.theme = theme
                user_profile.primary_color = primary_color

                neutral_primary = request.POST.get("neutral_primary")
                user_profile.neutral_primary = neutral_primary

                neutral_secondary = request.POST.get("neutral_secondary")
                user_profile.neutral_secondary = neutral_secondary

                user_profile.save()
                return redirect("appearance")

            elif request.POST.get("form_type") == "colorform2":
                secondary_color = request.POST.get("secondary_color")
                theme = request.POST.get("custom_secondary_color")
                user_profile.theme = theme
                user_profile.secondary_color = secondary_color

                hover_color = request.POST.get("hover_color")
                user_profile.hover_color = hover_color

                active_link_color = request.POST.get("active_link_color")
                user_profile.active_link_color = active_link_color

                user_profile.save()
                return redirect("appearance")

            elif request.POST.get("form_type") == "colorform3":
                tertiary_colors = request.POST.get("tertiary_color")
                theme = request.POST.get("custom_tertiary_color")
                user_profile.theme = theme
                user_profile.tertiary_color = tertiary_colors
                user_profile.save()
                return JsonResponse({"color": tertiary_colors})
                # return redirect('appearance')

            if request.POST.get("color_description") == "colorcode":
                try:
                    image_generation_form = AIcolorCodeGenerationForm(request.POST)

                    if image_generation_form.is_valid():
                        # Get the title from the image generation form
                        title = image_generation_form.cleaned_data["title"]

                        # Generating colors paletts using OpenAI API

                        # openai.api_key = settings.OPENAI_API_KEY

                        # color_prompt = f"Convert the following verbal description of a color palette into a set of 2 different palettes
                        # with list of 4 hexadecimal color code starting with primary color for cards (this color should be light) ,
                        # secondary color for background (should be lighter), tertiary color for text (this color should be extremely dark),
                        # active link color (this color should be different), additionally generate 3 more color's with first fpr hovering the links
                        # (this color should be light), while others should be contrasty first being primary neutral (should be medium light),
                        # second being neutral secondary (should be moderately light) : {title}."

                        # # Generate an image based on the user's input
                        # response = openai.Completion.create(
                        #     engine="gpt-3.5-turbo-instruct",
                        #     prompt=color_prompt,
                        #     max_tokens=400,
                        #     temperature=0.7,
                        # )

                        # generated_colors = response.choices[0].text.strip()

                        # if hex_codes:
                        #     return JsonResponse({"generated_colors": hex_codes})

                        """----------------------------------------------------------------"""

                        # Generating colors paletts using Gemini API
                        client = genai.Client(api_key=settings.GEMINI_API_KEY)

                        response = client.models.generate_content(
                            model="gemini-2.5-flash-lite",
                            contents=[
                                f"""
                                Create four distinct color palettes for a UI design system, with each palette containing at least 
                                seven different colors for the following elements: Primary Color (for cards, buttons, etc.), 
                                which should be light and stand out against the background; 
                                Secondary Color (for the foreground, background on the body, and bootstrap modal), 
                                which should be lighter than the primary color and suitable for larger background areas; 
                                Tertiary Color (for text color), which should be most darkest to ensure excellent readability 
                                against lighter backgrounds; Active Link Color (background color for active links), 
                                which should be distinct and different from the primary, secondary, and tertiary colors; 
                                Hover Color (for hovering over links, cards, buttons, etc. modrate dark that provides good contrast for light text and light dark text), 
                                which should be light and provide clear visual feedback on interaction; 
                                Neutral Primary (a contrasting, punchy color for specific UI elements, lighter dark when other colors are dark so that light tertiary color for text appears clearly), 
                                which should be medium-light and complement the other colors; 
                                and Neutral Secondary (light color for light mode, a slightly dark mid-tone color), 
                                which should be a shade that provides good contrast for light text, 
                                but is not excessively dark, making it suitable for subtle highlights or less dominant UI elements in dark mode.
                                Each palette should ensure the colors work harmoniously together for a balanced, aesthetically pleasing design suitable for web or app interfaces.
                                """
                                f": {title}."
                            ],
                        )

                        hex_codes = extract_hex_codes(response.text)
                        if hex_codes:
                            return JsonResponse({"generated_colors": "".join(hex_codes)})
                        else:
                            return JsonResponse({"error": "No hex codes found in the response."})

                except Exception as e:
                    error = str(e)

                    return JsonResponse({"error": error})

        form = AIcolorCodeGenerationForm()

        # profile = request.user.profile
        if request.method == "POST":
            form = UseColorFromImageForm(request.POST)
            if form.is_valid():
                use_colors_from_image = form.cleaned_data.get("use_colors_from_image", False)
                request.user.userprofile.use_colors_from_image = use_colors_from_image
                request.user.userprofile.save()
                return redirect("appearance")

        image_color_form = UseColorFromImageForm()

        # elif request.POST.get("dark_form_type") == 'darkform':
        #     primarycolor = request.POST.get('dark_primary_color')
        #     user_profile.primary_color = primarycolor

        #     secondarycolor = request.POST.get('dark_secondary_color')
        #     user_profile.secondary_color = secondarycolor

        #     tertiarycolors = request.POST.get('dark_tertiary_color')
        #     user_profile.tertiary_color = tertiarycolors

        #     activelink_color = request.POST.get('dark_active_link_color')
        #     user_profile.active_link_color = activelink_color

        #     hovercolor = request.POST.get('dark_hover_color')
        #     user_profile.hover_color = hovercolor

        #     neutralprimary_color = request.POST.get('dark_neutral_primary')
        #     user_profile.neutral_primary = neutralprimary_color

        #     neutralsecondary_color = request.POST.get('dark_neutral_secondary')
        #     user_profile.neutral_primary = neutralsecondary_color

        #     theme = request.POST.get('dark_theme')
        #     user_profile.theme = theme
        #     user_profile.save()

        # return redirect('appearance')

        # return redirect('appearance')

        return render(
            request,
            "testingapp/appearance.html",
            {
                "user_profile": user_profile,
                "form": form,
                "image_color_form": image_color_form,
            },
        )
    else:
        if request.method == "POST":
            guest_data = request.session.get("guest_user", {})

            form_type = request.POST.get("form_type")

            if form_type == "colorform":
                guest_data.update(
                    {
                        "primary_color": request.POST.get("primary_color", guest_data.get("primary_color", "#DBCBBD")),
                        "neutral_primary": request.POST.get(
                            "neutral_primary",
                            guest_data.get("neutral_primary", "#DFBB9D"),
                        ),
                        "neutral_secondary": request.POST.get(
                            "neutral_secondary",
                            guest_data.get("neutral_secondary", "#DBD7CB"),
                        ),
                        "theme": "custom",
                    }
                )

            elif form_type == "colorform2":
                guest_data.update(
                    {
                        "secondary_color": request.POST.get(
                            "secondary_color",
                            guest_data.get("secondary_color", "#F0ECE3"),
                        ),
                        "hover_color": request.POST.get("hover_color", guest_data.get("hover_color", "#9C938B")),
                        "active_link_color": request.POST.get(
                            "active_link_color",
                            guest_data.get("active_link_color", "#9F8772"),
                        ),
                        "theme": "custom",
                    }
                )

            elif form_type == "colorform3":
                guest_data.update(
                    {
                        "tertiary_color": request.POST.get(
                            "tertiary_color",
                            guest_data.get("tertiary_color", "#221e20"),
                        ),
                        "theme": "custom",
                    }
                )

            guest_uuid = guest_data.get("uuid")
            guest_name = guest_data.get("name")
            guest_email = guest_data.get("email")

            guest_data["uuid"] = guest_uuid
            guest_data["name"] = guest_name
            guest_data["email"] = guest_email

            request.session["guest_user"] = guest_data
            request.session.modified = True

        return render(request, "testingapp/appearance.html")


def reset_colors(request):
    if not request.guest_active:
        user_profile = UserProfile.objects.get(user=request.user)

        if request.method == "POST":
            if request.POST.get("default_form_type") == "defaultform":
                defaultprimary_color = request.POST.get("default_primary_color")
                user_profile.primary_color = defaultprimary_color

                defaultsecondary_color = request.POST.get("default_secondary_color")
                user_profile.secondary_color = defaultsecondary_color

                defaulttertiary_color = request.POST.get("default_tertiary_color")
                user_profile.tertiary_color = defaulttertiary_color

                defaultactivelink_color = request.POST.get("default_activelink_color")
                user_profile.active_link_color = defaultactivelink_color

                defaulthover_color = request.POST.get("default_hover_color")
                user_profile.hover_color = defaulthover_color

                defaultneutral_primary = request.POST.get("default_neutral_primary")
                user_profile.neutral_primary = defaultneutral_primary

                defaultneutral_secondary = request.POST.get("default_neutral_secondary")
                user_profile.neutral_secondary = defaultneutral_secondary

                theme = request.POST.get("default_theme")
                user_profile.theme = theme

                user_profile.save()

                return JsonResponse(
                    {
                        "defaultprimary_color": defaultprimary_color,
                        "defaultsecondary_color": defaultsecondary_color,
                        "theme": theme,
                        "defaulttertiary_color": defaulttertiary_color,
                        "defaultactivelink_color": defaultactivelink_color,
                        "defaulthover_color": defaulthover_color,
                    }
                )

            return render(request, "testingapp/appearance.html")

        else:
            # these colors are set by default using models.py not by these mentioned below
            user_profile.primary_color = "#DBCBBD"
            user_profile.secondary_color = "#F0ECE3"
            user_profile.tertiary_color = "#221e20"
            user_profile.active_link_color = "#9F8772"
            user_profile.hover_color = "#9C938B"
            user_profile.neutral_primary = "#DFBB9D"
            user_profile.neutral_secondary = "#DBD7CB"
            user_profile.theme = "default_theme"
            user_profile.save()

            return redirect("appearance")
    else:
        if request.method == "POST" and request.session.get("guest_user"):
            guest_user = request.session["guest_user"]
            guest_user.update(
                {
                    "primary_color": request.POST.get("default_primary_color"),
                    "secondary_color": request.POST.get("default_secondary_color"),
                    "tertiary_color": request.POST.get("default_tertiary_color"),
                    "active_link_color": request.POST.get("default_activelink_color"),
                    "hover_color": request.POST.get("default_hover_color"),
                    "neutral_primary": request.POST.get("default_neutral_primary"),
                    "neutral_secondary": request.POST.get("default_neutral_secondary"),
                    "theme": "default_theme",
                }
            )
            request.session.modified = True
            return JsonResponse({"theme": "default_theme"})

            # if 'guest_user' not in request.session:
            #     request.session['guest_user'] = {}

            # request.session['guest_user'].update({'primary_color': defaultprimary_color,'secondary_color': defaultsecondary_color,
            #     'tertiary_color': defaulttertiary_color,'active_link_color': defaultactivelink_color,'hover_color': defaulthover_color,
            #     'neutral_primary': defaultneutral_primary,'neutral_secondary': defaultneutral_secondary,'theme': theme,
            # })
            # request.session.modified = True

            # return JsonResponse({'role': 'guest','theme': theme,'primary': defaultprimary_color,'secondary': defaultsecondary_color,
            #     'tertiary': defaulttertiary_color,'active_link': defaultactivelink_color,'hover': defaulthover_color,
            #     'neutral_primary': defaultneutral_primary,'neutral_secondary': defaultneutral_secondary,
            # })

        return render(request, "testingapp/appearance.html")


def reset_dark_theme(request):
    if not request.guest_active:
        user_profile = UserProfile.objects.get(user=request.user)

        if request.method == "POST":
            if request.POST.get("default_dark_form_type") == "defaultdarkform":
                defdarkprimary_color = request.POST.get("def_dark_primary_color")
                user_profile.primary_color = defdarkprimary_color

                defdarksecondary_color = request.POST.get("def_dark_secondary_color")
                user_profile.secondary_color = defdarksecondary_color

                defdarktertiary_color = request.POST.get("def_dark_tertiary_color")
                user_profile.tertiary_color = defdarktertiary_color

                defdarkactivelink_color = request.POST.get("def_dark_activelink_color")
                user_profile.active_link_color = defdarkactivelink_color

                defdarkhover_color = request.POST.get("def_dark_hover_color")
                user_profile.hover_color = defdarkhover_color

                defdarkneutral_primary = request.POST.get("def_dark_neutral_primary")
                user_profile.neutral_primary = defdarkneutral_primary

                defdarkneutral_secondary = request.POST.get("def_dark_neutral_secondary")
                user_profile.neutral_secondary = defdarkneutral_secondary

                theme = request.POST.get("default_dark_theme")
                user_profile.theme = theme

                user_profile.save()

                # return redirect('appearance')

                return JsonResponse(
                    {
                        "defdarkprimary_color": defdarkprimary_color,
                        "defdarksecondary_color": defdarksecondary_color,
                        "theme": theme,
                        "defdarktertiary_color": defdarktertiary_color,
                        "defdarkactivelink_color": defdarkactivelink_color,
                        "defdarkhover_color": defdarkhover_color,
                    }
                )

            # return render(request, 'testingapp/appearance.html')

        else:
            user_profile.primary_color = "#414141"
            user_profile.secondary_color = "#4e4e4e"
            user_profile.tertiary_color = "#D9D9D9"
            user_profile.active_link_color = "#1A5F7A"
            user_profile.hover_color = "#526D82"
            user_profile.neutral_primary = "#4a5eab"
            user_profile.neutral_secondary = "#689ec8"
            user_profile.theme = "default_dark_theme"
            user_profile.save()

            return redirect("appearance")

            # user_profile = UserProfile.objects.get(user=request.user)
            # user_profile.primary_color = "#343434"
            # user_profile.secondary_color = "#464646"
            # user_profile.tertiary_color = "#D9D9D9"
            # user_profile.active_link_color = "#6d3b47"
            # user_profile.hover_color = "#766b65"
            # user_profile.theme = "Dark theme"
            # user_profile.save()
            # return redirect('appearance')

    else:
        if request.method == "POST" and request.session.get("guest_user"):
            guest_user = request.session["guest_user"]
            guest_user.update(
                {
                    "primary_color": request.POST.get("def_dark_primary_color", "#39393a"),
                    "secondary_color": request.POST.get("def_dark_secondary_color", "#252422"),
                    "tertiary_color": request.POST.get("def_dark_tertiary_color", "#f5f5dc"),
                    "active_link_color": request.POST.get("def_dark_activelink_color", "#829cbc"),
                    "hover_color": request.POST.get("def_dark_hover_color", "#6d6a75"),
                    "neutral_primary": request.POST.get("def_dark_neutral_primary", "#0077b6"),
                    "neutral_secondary": request.POST.get("def_dark_neutral_secondary", "#5c6b73"),
                    "theme": "default_dark_theme",
                }
            )
            request.session.modified = True
            return JsonResponse({"theme": "default_dark_theme"})

            # if 'guest_user' not in request.session:
            #     request.session['guest_user'] = {}

            # request.session['guest_user'].update({'primary_color': defdarkprimary_color,'secondary_color': defdarksecondary_color,
            #     'tertiary_color': defdarktertiary_color,'active_link_color': defdarkactivelink_color,'hover_color': defdarkhover_color,
            #     'neutral_primary': defdarkneutral_primary,'neutral_secondary': defdarkneutral_secondary,'theme': theme,
            # })
            # request.session.modified = True

            # return JsonResponse({'role': 'guest','theme': theme,'primary': defdarkprimary_color,'secondary': defdarksecondary_color,
            #     'tertiary': defdarktertiary_color,'active_link': defdarkactivelink_color,'hover': defdarkhover_color,
            #     'neutral_primary': defdarkneutral_primary,'neutral_secondary': defdarkneutral_secondary,
            # })

        return render(request, "testingapp/appearance.html")


def default_color_palette1(request):
    user_profile = UserProfile.objects.get(user=request.user)

    if request.method == "POST":
        # ai colors
        if request.POST.get("ai_color_palette").startswith("aiform"):
            # 7 colors in each form palette
            for i in range(1, 8):
                color_key = f"ai_color{i}"
                color_value = request.POST.get(color_key)

                # Handle each color_value as needed, for example:
                if color_key == "ai_color1":
                    user_profile.primary_color = color_value
                elif color_key == "ai_color2":
                    user_profile.secondary_color = color_value
                elif color_key == "ai_color3":
                    user_profile.tertiary_color = color_value
                elif color_key == "ai_color4":
                    user_profile.active_link_color = color_value
                elif color_key == "ai_color5":
                    user_profile.hover_color = color_value
                elif color_key == "ai_color6":
                    user_profile.neutral_primary = color_value
                elif color_key == "ai_color7":
                    user_profile.neutral_secondary = color_value

            theme = request.POST.get("ai_theme")
            user_profile.theme = theme
            user_profile.save()

        elif request.POST.get("ai_color_palette") == "saved_ai_form":
            aiprimary_color = request.POST.get("ai_primary_color")
            user_profile.primary_color = aiprimary_color

            aisecondary_color = request.POST.get("ai_secondary_color")
            user_profile.secondary_color = aisecondary_color

            aitertiary_color = request.POST.get("ai_tertiary_color")
            user_profile.tertiary_color = aitertiary_color

            aiactivelink_color = request.POST.get("ai_activelink_color")
            user_profile.active_link_color = aiactivelink_color

            aihover_color = request.POST.get("ai_hover_color")
            user_profile.hover_color = aihover_color

            aineutral_primary = request.POST.get("ai_neutral_primary")
            user_profile.neutral_primary = aineutral_primary

            aineutral_secondary = request.POST.get("ai_neutral_secondary")
            user_profile.neutral_secondary = aineutral_secondary

            theme = request.POST.get("ai_color_scheme")
            user_profile.theme = theme

            user_profile.save()
            return JsonResponse({"theme": theme})

    return render(request, "testingapp/appearance.html")
