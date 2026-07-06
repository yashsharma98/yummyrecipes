from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse

from ..models import (
    Follow,
    post,
    profile,
)
from ..search.extractors import extract_navigation
from ..search.search_manager import search_flow


def searchresults(request):
    query = request.GET.get("query", "").strip()

    # page navigation
    nav_url = extract_navigation(query)
    if nav_url:
        return redirect(nav_url)

    search_data = search_flow(query, request)

    recipe_results = (
        search_data["exact_recipes"] | search_data["filtered_recipes"] | search_data["semantic_recipes"] | search_data["partial_recipes"]
    ).distinct()
    profile_results = search_data["users"]

    has_results = recipe_results.exists() or profile_results.exists()

    recipe_description = None
    recipe_image_url = None

    context = {
        "query": query,
        "results": has_results,
        "profile_results": profile_results,
        "recipe_results": recipe_results,
        "show_google": search_data["show_google"],
        "show_kitchen_ai": search_data["show_kitchen_ai"],
        "recipe_description": recipe_description,
        "recipe_image_url": recipe_image_url,
    }

    return render(request, "yummyrecipes/searchresults.html", context)


def userchannel(request, first, pk, last=None):
    user = request.user
    user_profiles = profile.objects.all()
    profile_details = User.objects.get(pk=pk)

    if last is not None:
        try:
            total_user_recipes = post.objects.filter(author=profile_details).order_by("-date_post").all()

            category_dict = {}
            types = ["All", "Breakfast", "Lunch", "Evening Snack", "Dinner", "Veg", "Non-Veg"]

            all_posts = post.objects.filter(author=profile_details).order_by("-date_post")
            category_dict["All"] = all_posts

            for category in types[1:]:
                category_posts = (
                    post.objects.filter(author=profile_details).filter(Q(type__iexact=category) | Q(category__iexact=category)).order_by("-date_post")
                )

                category_dict[category] = category_posts

        except Exception as e:
            error_message = str(e)
            return render(request, "yummyrecipes/userchannelpage.html", {"error_message": error_message})

    else:
        try:
            return redirect(reverse("searchresults") + f"?query={first}")

        except Exception as e:
            error_message = str(e)
            return render(request, "yummyrecipes/userchannelpage.html")

    all_recipes = post.objects.filter().all()

    query = request.GET.get("follow_user")
    results = User.objects.filter(pk=pk)

    total_user_recipes = post.objects.filter(author=profile_details).order_by("-date_post").all()
    user_total_views = (
        post.objects.filter(author=profile_details).annotate(total_hits=Sum("hit_count_generic__hits")).aggregate(total=Sum("total_hits"))["total"]
    )
    user_followers_count = Follow.objects.filter(following=profile_details).count()

    user_social_links = profile.objects.get(user_id=profile_details)

    bio = profile_details.profile
    user_bio = bio.bio
    date_joined = profile_details.date_joined.date()

    absolute_url = request.build_absolute_uri()

    if request.user.is_authenticated:
        is_following = []
        for user in results:
            user_exists = Follow.objects.filter(follower=request.user, following=user).exists()
            is_following.append(user_exists)
        print("TYPES:", types)
        print("CATEGORY DICT:", category_dict.keys())
        return render(
            request,
            "yummyrecipes/userchannelpage.html",
            {
                "profile_details": profile_details,
                "user_profiles": user_profiles,
                "all_recipes": all_recipes,
                "total_user_recipes": total_user_recipes,
                "results": results,
                "query": query,
                "is_following": is_following,
                "user_total_views": user_total_views,
                "user_followers_count": user_followers_count,
                "user_social_links": user_social_links,
                "user_bio": user_bio,
                "date_joined": date_joined,
                "absolute_url": absolute_url,
                "types": types,
                "category_dict": category_dict,
            },
        )

    else:
        return render(
            request,
            "yummyrecipes/userchannelpage.html",
            {
                "profile_details": profile_details,
                "user_profiles": user_profiles,
                "all_recipes": all_recipes,
                "total_user_recipes": total_user_recipes,
                "user_total_views": user_total_views,
                "user_followers_count": user_followers_count,
                "user_social_links": user_social_links,
                "user_bio": user_bio,
                "date_joined": date_joined,
                "absolute_url": absolute_url,
                "types": types,
                "category_dict": category_dict,
            },
        )
