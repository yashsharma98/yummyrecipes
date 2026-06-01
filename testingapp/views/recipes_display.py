import base64
import datetime
import json
from datetime import timedelta
from functools import reduce
from io import BytesIO
from operator import or_

import qrcode
import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.http import (
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

# from django.core import serializers
from django.views.generic import ListView
from hitcount.views import HitCountDetailView, HitCountMixin
from notifications.signals import notify
from requests.exceptions import RequestException

from ..forms import (
    comment_form,
)
from ..models import BlogHistory, CreditSpentHistory, Follow, RecipeRecommendationHistory, comments, post, profile
from ..utils.history_helpers import get_historys_pk
from ..utils.recipes_helper import clean_ingredients, get_recommendations

API_KEY = settings.SPOONACULAR_API_KEY


def custom_cards(request, slug):
    try:
        veg_recipes = None
        nonveg_recipes = None
        new_recipes = None
        under_10_minutes = None

        end_date = datetime.datetime.now()
        start_date = end_date - timedelta(days=7)
        # current_recipes = []

        if slug == "veg_recipes":
            veg_recipes = post.objects.filter(category="Veg").order_by("-date_post")
            # current_recipes = veg_recipes

        elif slug == "nonveg_recipes":
            nonveg_recipes = post.objects.filter(category="Non-Veg").order_by("-date_post")
            # current_recipes = nonveg_recipes

        elif slug == "new_recipes":
            new_recipes = post.objects.filter(date_post__range=[start_date, end_date])
            # current_recipes = new_recipes

        elif slug == "under_10_minutes":
            under_10_minutes = post.objects.filter(timing__lte=10)
            # current_recipes = under_10_minutes

        return render(
            request,
            "testingapp/custom_cards.html",
            {
                "slug": slug,
                "veg_recipes": veg_recipes,
                "nonveg_recipes": nonveg_recipes,
                "new_recipes": new_recipes,
                "under_10_minutes": under_10_minutes,
            },
        )

    except Exception:
        return render(
            request,
            "testingapp/custom_cards.html",
            {"error_message": "An error occurred"},
        )


def cuisines(request, slug):
    try:
        indian_cuisine = None
        american_cuisine = None
        italian_cuisine = None

        if slug == "Indian Cuisine":
            indian_cuisine = post.objects.filter(cuisine="Indian cuisine").order_by("-date_post")

        elif slug == "American Cuisine":
            american_cuisine = post.objects.filter(cuisine="American cuisine").order_by("-date_post")

        elif slug == "Italian Cuisine":
            italian_cuisine = post.objects.filter(cuisine="Italian cuisine").order_by("-date_post")

        return render(
            request,
            "testingapp/cuisines.html",
            {
                "slug": slug,
                "indian_cuisine": indian_cuisine,
                "american_cuisine": american_cuisine,
                "italian_cuisine": italian_cuisine,
            },
        )

    except Exception:
        return render(request, "testingapp/cuisines.html", {"error_message": "An error occurred"})


class exploreRecipesView(HitCountMixin, ListView):
    model = post
    template_name = "testingapp/explore.html"
    ordering = ["-date_post"]
    context_object_name = "posts"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_dict = {}
        category_counts = {}

        types = {
            "All": "All",
            "Breakfast": "Breakfast",
            "Lunch": "Lunch",
            "Evening Snack": "Evening Snack",
            "Dinner": "Dinner",
            "Veg": "Veg",
            "Non-Veg": "Non-Veg",
            "Indian": "Indian cuisine",
            "American": "American cuisine",
            "Italian": "Italian cuisine",
        }

        all_posts = post.objects.order_by("-date_post")
        category_dict["All"] = all_posts
        category_counts["All"] = all_posts.count()

        for display, query in types.items():
            if display == "All":
                continue

            category_posts = post.objects.filter(Q(type__iexact=query) | Q(category__iexact=query) | Q(cuisine__iexact=query)).order_by("-date_post")

            category_dict[display] = category_posts
            category_counts[display] = category_posts.count()

        context.update(
            {
                "historys_pk": get_historys_pk(self.request.user),
                "category_dict": category_dict,
                "types": types,
                "category_counts": category_counts,
            }
        )
        return context


def get_recipe_nutrition_widget(ingredients):
    cleaned_ingredients = clean_ingredients(ingredients)

    url = "https://api.spoonacular.com/recipes/visualizeNutrition"
    data = {"ingredientList": cleaned_ingredients, "apiKey": API_KEY, "defaultCss": True}

    try:
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()

        return response.text

    except RequestException:
        return "Information is not unavailable"


class postDetailView(HitCountDetailView):
    model = post
    template_name = "testingapp/postdetail.html"
    context_object_name = "post"
    # slug_field = 'slug'
    count_hit = True

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        # Check if the user is authenticated and hasn't viewed the page yet
        if user.is_authenticated and not request.session.get(f"viewed_post_{self.get_object().pk}", False):
            blog_history = BlogHistory.objects.filter(user=user)
            blog_posts = [entry.blog_post for entry in blog_history]

            if self.get_object() in blog_posts:
                return super().dispatch(request, *args, **kwargs)

            # Check if the user has enough credits
            elif user.profile.credits >= 1:
                # Deduct 1 credit from the user's account
                user.profile.credits -= 1

                # Update the credits_spent field in the user's profile
                user.profile.credits_spent += 1

                # Create a new entry in CreditSpentHistory to record the credit spent
                CreditSpentHistory.objects.create(user=user, recipename=self.get_object(), amount=1)

                user.profile.save()
                # messages.success(request, "You have successfully viewed the page. 1 credit deducted.")

                # Set a session variable to view that the user has viewed the page
                request.session[f"viewed_post_{self.get_object().pk}"] = True

            else:
                error_msg = "Not enough credits!"
                messages.error(request, error_msg, extra_tags="no-more-credits")
                return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
                # return redirect('home')

        # Allowing unauthenticated user to view upto 5 recipes (any)
        elif not request.user.is_authenticated:
            request.session.setdefault("viewed_recipes", [])
            viewed_recipes = request.session["viewed_recipes"]

            recipe_id = self.get_object().pk

            if recipe_id not in viewed_recipes:
                if len(viewed_recipes) >= 5:
                    return redirect("topostlogin", recipe_id)

                viewed_recipes.append(recipe_id)
                request.session["viewed_recipes"] = viewed_recipes[:5]  # Limit to 5 recipes

        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        user = self.request.user
        if user.is_authenticated:
            RecipeRecommendationHistory.objects.filter(user=user, recipe=obj, clicked=False).update(clicked=True)

        return obj

    def get_context_data(self, pk=post.id, **kwargs):
        context = super().get_context_data(**kwargs)

        if not self.request.user.is_authenticated:
            viewed_recipes = self.request.session.get("viewed_recipes", [])
            context["viewed_recipe_count"] = len(viewed_recipes)
            context["viewed_recipe_ids"] = viewed_recipes
            viewed_posts = post.objects.filter(pk__in=viewed_recipes)
            context["viewed_posts"] = viewed_posts
            context["free_recipes_left"] = 5 - len(viewed_recipes)

        postrecipe = self.get_object()

        from ..ml.predictor import predict_recipe_time

        # using ml model to pred the recipe timings
        pred_time = predict_recipe_time(postrecipe)
        context["pred_time"] = pred_time

        # getting nutrition info from api
        query = postrecipe.title

        if query:
            try:
                api_url = "https://api.api-ninjas.com/v1/nutrition?query="
                api_request = requests.get(api_url + query, headers={"X-Api-Key": settings.NUTRITION_API_KEY})
                api_data = json.loads(api_request.content)

                if api_request.status_code == 200:
                    context["nutrition_info"] = api_data
                else:
                    context["nutrition_info_error"] = "Error occurred"

            except ConnectionError:
                context["nutrition_info_error"] = "Could not connect to Api"

            except Exception:
                api = "Error occured"
                context["nutrition_info_error"] = api

        recipe_id = self.kwargs["pk"]
        # Check if the recipe exists
        if not post.objects.filter(id=recipe_id).exists():
            raise ValueError(f"Recipe with {recipe_id} not found.")

        recommended_recipes = get_recommendations(recipe_id)
        context["recommended_recipes"] = recommended_recipes

        context["comments"] = comments.objects.filter(post_super=self.get_object()).order_by("date_comment")
        context["comments_count"] = comments.objects.filter(post_super=self.get_object()).count()

        form = comment_form()
        context["form"] = form

        # post_content = striptags(self.get_object().content)
        # recipe_title = self.get_object().title

        # gtts library for audio
        audio_file_path = f"{self.get_object().title}.mp3"

        context["audio_file_new"] = default_storage.url(audio_file_path)

        post_author = context["post"]
        author_name = post_author.author.username

        author = User.objects.get(username=author_name)
        context["author_recipes"] = post.objects.filter(author=author)

        context["hour"] = datetime.datetime.now().hour
        context["breakfast"] = post.objects.filter(type="Breakfast").all()
        context["lunch"] = post.objects.filter(type="Lunch").all()
        context["evesnack"] = post.objects.filter(type="Evening Snack").all()
        context["dinner"] = post.objects.filter(type="Dinner").all()
        context["all_recipes"] = post.objects.filter().all()
        context["trending_recipes"] = post.objects.order_by("-hit_count_generic__hits")[0:10]

        # context['recipe_img'] = recipe_img

        hit_count = self.request.META.get("REMOTE_ADDR")
        context["hit_count"] = hit_count

        trending_list = []

        recipe_name = []

        index_val = []

        trending_recipes = post.objects.order_by("-hit_count_generic__hits")[0:10]

        get_recipe = post.objects.filter(title=self.object.title)
        for i in trending_recipes:
            trending_list.append(i.title)

        for i in get_recipe:
            recipe_name.append(i.title)

        for i in recipe_name:
            for j in trending_list:
                if i == j:
                    a = trending_list.index(j) + 1
                    index_val.append(a)

        recipes_by_author = self.object

        total_recipes_by_author = post.objects.filter(author=recipes_by_author.author).count()

        context["total_recipes_by_author"] = total_recipes_by_author

        pk = self.kwargs["pk"]
        user = self.request.user

        # Create BlogHistory instance if the user is authenticated
        if user.is_authenticated:
            blog_post = get_object_or_404(post, id=pk)

            # Check if the blog_post already exists in BlogHistory for the user
            if not BlogHistory.objects.filter(user=user, blog_post=blog_post).exists():
                blog_history = BlogHistory(user=user, blog_post=blog_post)

            else:
                # If blog_history exists then update the timestamp
                blog_history = BlogHistory.objects.filter(user=user, blog_post=blog_post).first()
                blog_history.timestamp = timezone.now()
            blog_history.save()

        if user.is_authenticated:
            context["tot_posts_byuser"] = post.objects.filter(author=user).all().count()

        context["allrecipes"] = post.objects.all().order_by("-date_post").all().count()
        context["trnposts"] = post.objects.order_by("-hit_count_generic__hits")[0:4]

        context["check"] = index_val
        context["fetched_recipe"] = recipe_name
        context["top_10_trend_recipes"] = trending_list

        recipe_author = post_author.author.id
        followers_count = Follow.objects.filter(following=recipe_author).count()
        context["followers"] = followers_count

        recipe_author_username = post_author.author
        results = User.objects.filter(reduce(or_, [Q(username__icontains=recipe_author_username)]))

        if user.is_authenticated:
            is_following = []
            user_results = []
            for user in results:
                user_exists = Follow.objects.filter(follower=self.request.user, following=user).exists()
                is_following.append(user_exists)
                user_results.append(user)

            context["is__following"] = is_following
            context["user__results"] = user_results

        user_profiles = profile.objects.all()

        context["user_profiles"] = user_profiles

        recipe = self.get_object()

        nutrition_widget = get_recipe_nutrition_widget(recipe.ingredients)

        if "Information is not unavailable" in nutrition_widget:
            context["nutrition_error"] = True
            context["nutrition_widget"] = None
        else:
            context["nutrition_error"] = False
            context["nutrition_widget"] = nutrition_widget

        # for shopping list
        recipe_object = self.get_object()

        context["ingredients"] = recipe_object.ingredients

        # QR code generation
        post_url = get_object_or_404(post, pk=self.kwargs["pk"])
        recipe_url = self.request.build_absolute_uri(post_url.get_recipe_url())

        qr = qrcode.QRCode(
            version=1,
            box_size=7,
            border=0,
        )
        qr.add_data(recipe_url)
        qr.make(fit=True)

        if user.is_authenticated:
            fill_color = self.request.user.userprofile.tertiary_color
            back_color = self.request.user.userprofile.secondary_color
        if user.is_authenticated and self.request.user.userprofile.theme == "transparent_theme":
            fill_color = self.request.user.userprofile.tertiary_color
            back_color = "Transparent"
        else:
            fill_color = "#000000"
            back_color = "#FFFFFF"

        img = qr.make_image(fill_color=fill_color, back_color=back_color)

        # Saving the image in memory
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        img_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

        context["img_data"] = img_data
        return context

    def get_redirect_url(self, *args, **kwargs):
        pk = self.kwargs.get("pk")
        return reverse("compare_recipes", kwargs={"pk": pk})

    def strip_tags(self, html):
        soup = BeautifulSoup(html, "html.parser")
        return soup.get_text()

    def post(self, request, *args, **kwargs):
        comment_text = request.POST.get("comt", "").strip()

        if not comment_text:
            return JsonResponse({"error": "Empty comment"}, status=400)

        post_object = self.get_object()

        com = comments.objects.create(
            post_super=post_object,
            comment_user=request.user,
            comment=comment_text,
        )

        if request.user != post_object.author:
            notify.send(
                sender=request.user,
                recipient=post_object.author,
                verb="commented",
                action_object=post_object,
                description=comment_text,
            )

        return JsonResponse(
            {
                "comment": com.comment,
                "date": com.date_comment.strftime("%b %d, %Y"),
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "profile_img": request.user.profile.profile_img.url,
            }
        )

        # Handling translation
        # if "translate_content" in request.POST and "post_content" in request.POST:
        #     post_content = request.POST["post_content"]
        #     return self.translate_content(post_content)


class trendingRecipesView(HitCountMixin, ListView):
    model = post
    template_name = "testingapp/trending.html"
    context_object_name = "posts"

    def get_queryset(self):
        # Fetch cached trending posts
        cached = cache.get("trending_posts")
        if cached:
            ids = [p["id"] for p in cached]
            qs = post.objects.filter(id__in=ids).select_related("author")
            # Keep same order as cached list
            return sorted(qs, key=lambda x: ids.index(x.id))

        # Fallback (if cache is empty)
        return (
            post.objects.select_related("author")
            .annotate(
                total_hits=Coalesce(F("hit_count_generic__hits"), 0),
                total_likes=Count("likes", distinct=True),
            )
            .order_by("-total_hits", "-total_likes", "-date_post")[:20]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context.update(
            {
                "historys_pk": get_historys_pk(user) if user.is_authenticated else [],
            }
        )
        return context


def refresh_recipes(request):
    hour = datetime.datetime.now().hour

    if hour < 4:
        meal_posts = post.objects.filter(type="Dinner").order_by("-hit_count_generic__hits", "-date_post")
    elif hour < 12:
        meal_posts = post.objects.filter(type="Breakfast").order_by("-hit_count_generic__hits", "-date_post")
    elif hour < 17:
        meal_posts = post.objects.filter(type="Lunch").order_by("-hit_count_generic__hits", "-date_post")
    elif hour < 19:
        meal_posts = post.objects.filter(type="Evening Snack").order_by("-hit_count_generic__hits", "-date_post")
    else:
        meal_posts = post.objects.filter(type="Dinner").order_by("-hit_count_generic__hits", "-date_post")

    html = render_to_string(
        "testingapp/recipes_section.html",
        {
            "meal_posts": meal_posts,
        },
        request=request,
    )

    return JsonResponse({"html": html})


# class trendingRecipesView(HitCountMixin, ListView):
#     model = post
#     template_name = "testingapp/trending.html"
#     # ordering = ['-date_post']
#     context_object_name = "posts"

#     def get_context_data(self, **kwargs):
#         context = super(trendingRecipesView, self).get_context_data(**kwargs)
#         user = self.request.user

#         hour = datetime.datetime.now().hour

#         counts = post.objects.order_by("-hit_count_generic__hits")

#         tot_posts_byuser = 0

#         if self.request.user.is_authenticated:
#             tot_posts_byuser = post.objects.filter(author=user).all().count()

#         context = {
#             "hour": hour,
#             "counts": counts,
#             "tot_posts_byuser": tot_posts_byuser,
#             "historys_pk": get_historys_pk(self.request.user),
#         }
#         return context
