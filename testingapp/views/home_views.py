import datetime

from django.core.cache import cache
from django.db.models import Prefetch, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView

from testingapp.services.recipe_recommender import default_recommendations, personalized_recommendations

from ..models import Follow, post, profile
from ..tasks.home_tasks import update_popular_recipes_cache
from ..utils.context_builders import build_meal_context
from ..utils.home_utils import get_meal_posts, get_random_post, get_trending_recipes


def landingpg(request):
    if getattr(request, "guest_active", False):
        return redirect("home")
    return render(request, "testingapp/landingpg.html")


class HomeView(ListView):
    model = post
    template_name = "testingapp/home.html"
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

        meal_posts, meal_type = get_meal_posts()
        context["meal_posts"] = meal_posts
        context["meal_type"] = meal_type
        context["random_obj"] = get_random_post()
        context["popular_recipe"] = cache.get("popular_recipes") or []
        context["trending_recipes"] = get_trending_recipes()
        context["recommended_recipes_list"] = cache.get("recommended_recipes") or []

        # later add celery beat schedule in settings.py
        if not cache.get("popular_recipes"):
            try:
                update_popular_recipes_cache.delay()
            except Exception:
                pass

        context.update(build_meal_context(meal_posts, meal_type))
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
                recipes_preference = meal_posts
                context["preference_fallback_type"] = meal_type
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

        return list(post.objects.filter(**filters).order_by("-hit_count_generic__hits", "-date_post")[:12]) if filters else []
