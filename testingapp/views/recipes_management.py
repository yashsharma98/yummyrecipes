from io import BytesIO

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import (
    Http404,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.html import strip_tags
from django.views.generic import (
    DeleteView,
)
from google import genai
from google.genai import types
from notifications.signals import notify
from PIL import Image

from ..forms import (
    post_form,
)
from ..models import CreditHistory, photo, post, profile
from ..tasks.home_tasks import update_user_taste_profile


class deleteRecipes(DeleteView):
    model = post
    template_name = "testingapp/delete.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response_data = {"success": False}

        try:
            self.object = self.get_object()
            if self.object.author == self.request.user:
                # Deduct credits logic
                if self.request.user.profile.earned_credits >= 2 and self.request.user.profile.credits <= 2:
                    self.request.user.profile.earned_credits -= 2
                elif self.request.user.profile.earned_credits <= 2 and self.request.user.profile.credits >= 2:
                    self.request.user.profile.credits -= 2

                self.request.user.profile.save()

                CreditHistory.objects.create(user=self.request.user, credit_action="deleted", amount=-2)
                recipe_title = self.object.title
                response = super().form_valid(form)

                if response.status_code == 302:
                    response_data["success"] = True
                    response_data["title"] = recipe_title
                else:
                    response_data["error"] = "An error occurred during deletion"
            else:
                response_data["error"] = "You can't delete this post"
        except Exception:
            response_data["error"] = "An error occurred during deletion"

        return JsonResponse(response_data)


@login_required
def like_view(request):
    user = request.user
    if request.method == "POST":
        try:
            post_id = request.POST.get("post_id")
            post_obj = post.objects.get(id=post_id)
            profiles = profile.objects.get(user=user)

            with transaction.atomic():
                # Check if user is the author
                is_author = user == post_obj.author

                # Check if the user has already disliked the recipe
                removefromdislike = False
                if profiles in post_obj.dislikes.all():
                    post_obj.dislikes.remove(profiles)
                    removefromdislike = True

                    # Restore credit for removing dislike (only if not author)
                    if not is_author:
                        post_obj.author.profile.credits += 1
                        post_obj.author.profile.earned_credits += 1
                        post_obj.author.profile.save()

                        CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="earned")

                # Check if already liked
                if profiles in post_obj.likes.all():
                    # Unlike
                    post_obj.likes.remove(profiles)
                    action = "remove"

                    # Remove credit (only if not author)
                    if not is_author:
                        post_obj.author.profile.credits = max(0, post_obj.author.profile.credits - 1)
                        post_obj.author.profile.earned_credits = max(0, post_obj.author.profile.earned_credits - 1)
                        post_obj.author.profile.save()

                        CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="deleted")
                else:
                    # Like
                    post_obj.likes.add(profiles)
                    action = "added"

                    # Add credit (only if not author)
                    if not is_author:
                        post_obj.author.profile.credits += 1
                        post_obj.author.profile.earned_credits += 1
                        post_obj.author.profile.save()

                        CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="earned")

                        # Notify the author of the post
                        notify.send(
                            sender=user,
                            recipient=post_obj.author,
                            verb="liked",
                            action_object=post_obj,
                        )

                post_obj.save()

            # Update the user's taste profile for recipe recommendation
            update_user_taste_profile.delay(user.id)

            return JsonResponse(
                {
                    "total_likes": post_obj.total_likes(),
                    "total_dislikes": post_obj.total_dislikes(),
                    "removefromdislike": removefromdislike,
                    "action": action,
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)})
    else:
        return JsonResponse({"error": "Invalid request!"})


@login_required
def dislike_view(request):
    user = request.user
    if request.method == "POST":
        try:
            post_id = request.POST.get("post_id")
            post_obj = post.objects.get(id=post_id)
            profiles = profile.objects.get(user=user)

            with transaction.atomic():
                # Check if user is the author
                is_author = user == post_obj.author

                # Check if already disliked
                if profiles in post_obj.dislikes.all():
                    # Remove dislike
                    post_obj.dislikes.remove(profiles)
                    action = "remove"

                    # Restore credit (only if not author)
                    if not is_author:
                        post_obj.author.profile.credits += 1
                        post_obj.author.profile.earned_credits += 1
                        post_obj.author.profile.save()

                        CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="earned")

                    removefromlike = False
                else:
                    # Add dislike
                    post_obj.dislikes.add(profiles)
                    action = "added"

                    # If liked before, remove like
                    removefromlike = False
                    if profiles in post_obj.likes.all():
                        post_obj.likes.remove(profiles)
                        removefromlike = True

                        # Remove credit for like removal (only if not author)
                        if not is_author:
                            post_obj.author.profile.credits = max(0, post_obj.author.profile.credits - 1)
                            post_obj.author.profile.earned_credits = max(0, post_obj.author.profile.earned_credits - 1)
                            post_obj.author.profile.save()

                            CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="deleted")

                    # Remove credit for dislike (only if not author)
                    if not is_author:
                        post_obj.author.profile.credits = max(0, post_obj.author.profile.credits - 1)
                        post_obj.author.profile.earned_credits = max(0, post_obj.author.profile.earned_credits - 1)
                        post_obj.author.profile.save()

                        CreditHistory.objects.create(user=post_obj.author, amount=1, credit_action="deleted")

                        # Notify author
                        notify.send(
                            sender=user,
                            recipient=post_obj.author,
                            verb="disliked",
                            action_object=post_obj,
                        )

                post_obj.save()

            update_user_taste_profile.delay(user.id)

            return JsonResponse(
                {
                    "total_dislikes": post_obj.total_dislikes(),
                    "total_likes": post_obj.total_likes(),
                    "removefromlike": removefromlike,
                    "action": action,
                }
            )

        except Exception as e:
            return JsonResponse({"error": str(e)})

    return JsonResponse({"error": "Invalid request!"})


def send_post_email(request, post_instance, uploaded_files=None, generated_path=None):
    user = request.user
    profile = user.profile

    if not profile.send_email:
        return

    subject = post_instance.title
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    name = user.first_name
    date_posted = post_instance.date_post.date()
    post_timing = post_instance.date_post.strftime("%I:%M %p")

    post_url = request.build_absolute_uri(reverse("viewpost", kwargs={"pk": post_instance.pk}))

    context = {
        "name": name,
        "title": post_instance.title,
        "date_posted": date_posted,
        "post_timing": post_timing,
        "post_url": post_url,
    }

    html_message = render_to_string("testingapp/email_template.html", context)
    plain_message = strip_tags(html_message)

    email = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
    email.attach_alternative(html_message, "text/html")

    try:
        email.send()
    except Exception as e:
        return JsonResponse({"error": str(e)})


@login_required(login_url="login")
def post_post_view(request):
    post_count = post.objects.filter(author=request.user).count()
    request.session["count"] = post_count

    if request.method == "POST":
        if request.POST.get("img_type") == "mainimage":
            try:
                title = request.POST.get("title")

                if not settings.GEMINI_API_KEY:
                    return JsonResponse({"error": "API key missing"})

                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[f"Generate a realistic food image of: {title}"],
                    config=types.GenerateContentConfig(response_modalities=["Image"]),
                )

                for part in response.candidates[0].content.parts:
                    if part.inline_data is not None:
                        image_data = part.inline_data.data

                        image = Image.open(BytesIO(image_data)).convert("RGB")
                        buffer = BytesIO()
                        image.save(buffer, format="JPEG", quality=70, optimize=True)

                        filename = f"generated/{title.replace(' ', '_')}.jpg"
                        saved_path = default_storage.save(filename, ContentFile(buffer.getvalue()))

                        image_url = default_storage.url(saved_path)

                        return JsonResponse({"image_url": image_url, "saved_path": saved_path})

                return JsonResponse({"error": "Image generation failed"})

            except Exception as e:
                return JsonResponse({"error": str(e)})

        form = post_form(request.POST)
        uploaded_files = request.FILES.getlist("image")
        generated_path = request.POST.get("image_path")

        if uploaded_files and generated_path:
            return render(
                request,
                "testingapp/createpost.html",
                {"form": form, "newrecipe_error_message": "Choose either generated image OR upload image."},
            )

        if not uploaded_files and not generated_path:
            return render(
                request,
                "testingapp/createpost.html",
                {"form": form, "newrecipe_error_message": "Please upload or generate one image."},
            )

        if form.is_valid():
            title = form.cleaned_data["title"]

            # duplicate recipe title for same user
            if post.objects.filter(author=request.user, title__iexact=title).exists():
                return render(request,"testingapp/createpost.html",
                    {"form": form, "newrecipe_error_message": "You have already have a recipe with this title!"})
            
            post_instance = form.save(commit=False)
            post_instance.author = request.user
            post_instance.save()
            form.save_m2m()

            # manual upload image
            if uploaded_files:
                for file in uploaded_files:
                    photo.objects.create(feed=post_instance, image=file)

            # generated image
            if generated_path:
                photo.objects.create(feed=post_instance, image=generated_path)

            request.user.profile.earned_credits += 4
            request.user.profile.save()

            CreditHistory.objects.create(user=request.user, credit_action="new_recipe", amount=4)

            send_post_email(
                request=request,
                post_instance=post_instance,
                uploaded_files=uploaded_files,
                generated_path=generated_path,
            )

            request.session["success_message"] = post_instance.title
            request.session["is_form_submitted"] = True

            return redirect("home")

        return render(request, "testingapp/createpost.html", {"form": form, "newrecipe_error_message": "Form invalid."})

    form = post_form()
    return render(request, "testingapp/createpost.html", {"post_count": post_count, "form": form})


@login_required(login_url="login")
def Updaterecipeview(request, title, pk, *args, **kwargs):
    recipes = post.objects.get(title=title, pk=pk)

    if recipes.author != request.user:
        raise Http404

    if request.method == "POST":
        if "delete_image" in request.POST:
            image_id = request.POST.get("delete_image")
            if image_id and image_id.isdigit():
                photo.objects.filter(pk=int(image_id), feed=recipes).delete()
            return redirect("updaterecipe", title=title, pk=pk)

        for img in recipes.photo_set.all():
            new_image = request.FILES.get(f"change_image_{img.pk}")
            if new_image:
                img.image = new_image
                img.save()

        add_image = request.FILES.get("add_more_image")
        if add_image and recipes.photo_set.count() < 2:
            photo.objects.create(feed=recipes, image=add_image)

        form = post_form(request.POST, instance=recipes)

        if form.is_valid():
            updated_recipe = form.save()

            request.session["update_recipe_message"] = updated_recipe.title
            return redirect("dashboard")

    else:
        form = post_form(instance=recipes)

    return render(
        request,
        "testingapp/updaterecipe.html",
        {
            "form": form,
            "recipes": recipes,
            "image_count": recipes.photo_set.count(),
        })
