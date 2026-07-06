import datetime
from datetime import timedelta
from random import sample

from django.core.cache import cache
from django.db.models import Count, Prefetch, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView

from yummyrecipes.services.recipe_recommender import default_recommendations, personalized_recommendations

from ..models import Follow, photo, post, profile
from ..tasks.home_tasks import update_popular_recipes_cache

# from ..utils.context_builders import build_meal_context
# from ..utils.home_utils import get_meal_posts, get_random_post, get_trending_recipes
from ..utils.home_utils import get_random_post, get_trending_recipes


def landingpg(request):
    if getattr(request, "guest_active", False):
        return redirect("home")

    featured_recipes = (
        post.objects.prefetch_related(Prefetch("photo_set", queryset=photo.objects.only("image", "feed_id")))
        .annotate(num_likes=Count("likes"))
        .order_by("-views", "-num_likes", "-date_post")[:4]
    )

    cuisine_list = ["Indian cuisine", "American cuisine", "Italian cuisine"]

    cuisine_data = {}

    for cuisine in cuisine_list:
        recipe = post.objects.filter(cuisine=cuisine).prefetch_related("photo_set").order_by("-views").first()

        cuisine_data[cuisine.lower().replace(" ", "_")] = {"recipe": recipe, "image": recipe.photo_set.first() if recipe else None}

    context = {
        "featured_recipes": featured_recipes,
        "indian_recipe": cuisine_data["indian_cuisine"]["recipe"],
        "american_recipe": cuisine_data["american_cuisine"]["recipe"],
        "italian_recipe": cuisine_data["italian_cuisine"]["recipe"],
        "indian_image": cuisine_data["indian_cuisine"]["image"],
        "american_image": cuisine_data["american_cuisine"]["image"],
        "italian_image": cuisine_data["italian_cuisine"]["image"],
    }

    return render(request, "yummyrecipes/landingpg.html", context)


class HomeView(ListView):
    model = post
    template_name = "yummyrecipes/home.html"
    ordering = ["-date_post"]
    context_object_name = "posts"
    count_hit = True

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return post.objects.filter(author=user).select_related("author").prefetch_related("likes", "dislikes")
        return post.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        guest_user = self.request.session.get("guest_user")
        guest_active = bool(guest_user and not user.is_authenticated)

        # meal_posts, meal_type = get_meal_posts()
        # context["meal_posts"] = meal_posts
        # context["meal_type"] = meal_type

        hour = datetime.datetime.now().hour

        if 6 <= hour < 12:
            active_meal = "Breakfast"
        elif 12 <= hour < 16:
            active_meal = "Lunch"
        elif 16 <= hour < 18:
            active_meal = "Snacks"
        else:
            active_meal = "Dinner"

        context["active_meal"] = active_meal

        base_qs = post.objects.select_related("author").prefetch_related("photo_set")

        breakfast_posts = base_qs.filter(type="Breakfast").order_by("-hit_count_generic__hits", "-date_post")[:10]

        lunch_posts = base_qs.filter(type="Lunch").order_by("-hit_count_generic__hits", "-date_post")[:10]

        snack_posts = base_qs.filter(type="Evening Snack").order_by("-hit_count_generic__hits", "-date_post")[:10]

        dinner_posts = base_qs.filter(type="Dinner").order_by("-hit_count_generic__hits", "-date_post")[:10]

        veg_posts = base_qs.filter(category="Veg").order_by("-hit_count_generic__hits", "-date_post")[:10]

        nonveg_posts = base_qs.filter(category="Non-Veg").order_by("-hit_count_generic__hits", "-date_post")[:10]

        new_posts = base_qs.filter(date_post__gte=timezone.now() - timedelta(days=7)).order_by("-date_post")[:10]

        quick_posts = base_qs.filter(timing__lte=10).order_by("-hit_count_generic__hits", "-date_post")[:10]

        indian_posts = base_qs.filter(cuisine="Indian cuisine").order_by("-hit_count_generic__hits", "-date_post")[:10]

        american_posts = base_qs.filter(cuisine="American cuisine").order_by("-hit_count_generic__hits", "-date_post")[:10]

        italian_posts = base_qs.filter(cuisine="Italian cuisine").order_by("-hit_count_generic__hits", "-date_post")[:10]

        context["recipe_tabs"] = {
            "Breakfast": breakfast_posts,
            "Lunch": lunch_posts,
            "Snacks": snack_posts,
            "Dinner": dinner_posts,
            "Veg": veg_posts,
            "Non-Veg": nonveg_posts,
            "New": new_posts,
            "10 Min": quick_posts,
        }

        context["cuisine_tabs"] = {
            "Indian": indian_posts,
            "American": american_posts,
            "Italian": italian_posts,
        }

        context["combined_recipe"] = {
            **context["recipe_tabs"],
            **context["cuisine_tabs"],
        }

        # Used by frontend tabs
        # context["meal_recipes"] = {
        #     "Breakfast": breakfast_posts,
        #     "Lunch": lunch_posts,
        #     "Snacks": snack_posts,
        #     "Dinner": dinner_posts,
        # }

        context["random_obj"] = get_random_post()
        context["popular_recipe"] = cache.get("popular_recipes") or []
        context["trending_recipes"] = get_trending_recipes()
        context["recommended_recipes_list"] = cache.get("recommended_recipes") or []

        ids = list(post.objects.values_list("id", flat=True))
        random_ids = sample(ids, min(12, len(ids)))

        context["all_urecipe"] = post.objects.filter(id__in=random_ids)

        # later add celery beat schedule in settings.py
        if not cache.get("popular_recipes"):
            try:
                update_popular_recipes_cache.delay()
            except Exception:
                pass

        # context.update(build_meal_context(meal_posts, meal_type))
        context.update(
            {
                "date": datetime.date.today(),
                "hour": datetime.datetime.now().hour,
                "monthstr": datetime.date.today().strftime("%B"),
                "current_time": timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
                "guest_active": guest_active,
            }
        )

        if user.is_authenticated:
            following_ids = list(Follow.objects.filter(follower=user).values_list("following_id", flat=True))

            if following_ids:
                recent_posts_prefetch = Prefetch(
                    "user__post_set", queryset=post.objects.select_related("author").order_by("-date_post")[:5], to_attr="recent_posts"
                )
                following_profiles = profile.objects.filter(user_id__in=following_ids).select_related("user").prefetch_related(recent_posts_prefetch)

                following_user_posts = {f_profile: f_profile.user.recent_posts for f_profile in following_profiles if f_profile.user.recent_posts}
            else:
                following_user_posts = {}

            context["following_user_posts"] = following_user_posts

            u_profile = getattr(user, "profile", None)
            recipes_preference = self.preferred_recipes(u_profile) if u_profile else []

            if not recipes_preference:
                # recipes_preference = meal_posts
                # context["preference_fallback_type"] = meal_type
                pass
            else:
                context["recipes_preference"] = recipes_preference

            context["recommended_recipes"] = personalized_recommendations(user, limit=12)

            context["success_text"] = self.request.session.pop("success_message", None)

        else:
            context["recommended_recipes"] = default_recommendations(user, limit=12)
            context["following_user_posts"] = []
            context["recipes_preference"] = []

        rice_and_paneer = cache.get("rice_paneer_lists")
        if not rice_and_paneer:
            all_posts = post.objects.only("id", "title").filter(Q(title__icontains="rice") | Q(title__icontains="paneer")).order_by("-date_post")

            rice_list = []
            paneer_list = []
            for p in all_posts:
                title_lower = p.title.lower()
                if "rice" in title_lower:
                    rice_list.append(p)
                if "paneer" in title_lower:
                    paneer_list.append(p)

            rice_and_paneer = {"rice": rice_list, "paneer": paneer_list}
            cache.set("rice_paneer_lists", rice_and_paneer, 1800)

        context["rice_recipe_list"] = rice_and_paneer["rice"]
        context["panner_recipe_list"] = rice_and_paneer["paneer"]

        return context

    def preferred_recipes(self, u_profile):
        filters = {}
        if u_profile.preference_type and u_profile.preference_type != "Select":
            filters["type"] = u_profile.preference_type[:-8]
        if u_profile.preference_category and u_profile.preference_category != "Select":
            filters["category"] = u_profile.preference_category[:-8]
        if u_profile.preference_cuisine and u_profile.preference_cuisine != "Select":
            filters["cuisine"] = u_profile.preference_cuisine

        return list(post.objects.filter(**filters).order_by("-hit_count_generic__hits", "-date_post")[:10]) if filters else []
