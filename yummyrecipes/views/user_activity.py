from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Max, Sum
from django.http import (
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from notifications.models import Notification
from notifications.signals import notify

from ..decorators import login_or_guest_required
from ..forms import (
    FeedbackForm,
)
from ..models import (
    Feedback,
    Follow,
    post,
)


def likes_context(request):
    if request.guest_active:
        return {
            "liked_recipes": [],
            "received_likes_recipes": [],
            "top_liked_recipes": [],
            "total_liked_recipes": 0,
            "total_received_likes": 0,
            "top_likes": 0,
        }

    user = request.user

    liked_recipes = post.objects.filter(likes__user=user).annotate(num_likes=Count("likes")).order_by("-num_likes", "-date_post").distinct()

    received_likes_recipes = (
        post.objects.filter(author=user, likes__isnull=False).annotate(num_likes=Count("likes")).order_by("-num_likes").distinct()
    )

    top_liked_recipes = received_likes_recipes[:5]

    top_likes = received_likes_recipes.aggregate(most_likes=Max("num_likes"))["most_likes"] or 0

    return {
        "liked_recipes": liked_recipes,
        "received_likes_recipes": received_likes_recipes,
        "top_liked_recipes": top_liked_recipes,
        "total_liked_recipes": liked_recipes.count(),
        "total_received_likes": received_likes_recipes.count(),
        "top_likes": top_likes,
    }


@login_or_guest_required
def dashboard_likes(request):
    return render(
        request,
        "yummyrecipes/dashboard/likes/likes.html",
        likes_context(request),
    )


@login_or_guest_required
def dashboard_liked_recipes(request):
    return render(
        request,
        "yummyrecipes/dashboard/likes/liked_recipes.html",
        likes_context(request),
    )


@login_or_guest_required
def dashboard_likes_received(request):
    return render(
        request,
        "yummyrecipes/dashboard/likes/likes_received.html",
        likes_context(request),
    )


@login_or_guest_required
def dashboard_top_liked_recipes(request):
    return render(
        request,
        "yummyrecipes/dashboard/likes/top_liked_recipes.html",
        likes_context(request),
    )


@login_or_guest_required
def dashboard_dislikes(request):
    return render(
        request,
        "yummyrecipes/dashboard/dislikes/dislikes.html",
        dislikes_context(request),
    )


def dislikes_context(request):
    if request.guest_active:
        return {
            "disliked_recipes": [],
            "received_dislikes_recipes": [],
            "top_disliked_recipes": [],
            "total_disliked_recipes": 0,
            "total_received_dislikes": 0,
            "top_dislikes": 0,
        }

    user = request.user

    # Recipes this user disliked
    disliked_recipes = (
        post.objects.filter(dislikes__user=user).annotate(num_dislikes=Count("dislikes")).order_by("-num_dislikes", "-date_post").distinct()
    )

    # User's recipes that received dislikes
    received_dislikes_recipes = (
        post.objects.filter(author=user, dislikes__isnull=False).annotate(num_dislikes=Count("dislikes")).order_by("-num_dislikes").distinct()
    )

    # Top 5 most disliked recipes
    top_disliked_recipes = received_dislikes_recipes[:5]

    top_dislikes = received_dislikes_recipes.aggregate(most_dislikes=Max("num_dislikes"))["most_dislikes"] or 0

    return {
        "disliked_recipes": disliked_recipes,
        "received_dislikes_recipes": received_dislikes_recipes,
        "top_disliked_recipes": top_disliked_recipes,
        "total_disliked_recipes": disliked_recipes.count(),
        "total_received_dislikes": received_dislikes_recipes.count(),
        "top_dislikes": top_dislikes,
    }


@login_or_guest_required
def dashboard_disliked_recipes(request):
    return render(
        request,
        "yummyrecipes/dashboard/dislikes/disliked_recipes.html",
        dislikes_context(request),
    )


@login_or_guest_required
def dashboard_dislikes_received(request):
    return render(
        request,
        "yummyrecipes/dashboard/dislikes/dislikes_received.html",
        dislikes_context(request),
    )


@login_or_guest_required
def dashboard_top_disliked_recipes(request):
    return render(
        request,
        "yummyrecipes/dashboard/dislikes/top_disliked_recipes.html",
        dislikes_context(request),
    )


@login_or_guest_required
def dashboard_views(request):
    return render(
        request,
        "yummyrecipes/dashboard/views/views.html",
        views_context(request),
    )


def views_context(request):
    if request.guest_active:
        return {
            "year_data": [],
            "top_viewed_recipes": [],
            "all_recipes": [],
            "total_views": 0,
            "average_views": 0,
            "highest_views": 0,
        }

    user = request.user

    recipes = post.objects.filter(author=user).annotate(view_count=Sum("hit_count_generic__hits")).order_by("-date_post")

    total_views = recipes.aggregate(total=Sum("view_count"))["total"] or 0

    average_views = recipes.aggregate(avg=Avg("view_count"))["avg"] or 0

    highest_views = recipes.aggregate(max_views=Max("view_count"))["max_views"] or 0

    top_viewed_recipes = recipes.order_by("-view_count", "-date_post")[:5]

    distinct_years = recipes.dates("date_post", "year").reverse()

    year_data = []

    for year in distinct_years:
        yearly_recipes = recipes.filter(date_post__year=year.year).order_by("-view_count", "-date_post")

        year_data.append(
            {
                "year": year.year,
                "recipes": yearly_recipes,
                "recipe_count": yearly_recipes.count(),
                "total_views": yearly_recipes.aggregate(total=Sum("view_count"))["total"] or 0,
                "average_views": yearly_recipes.aggregate(avg=Avg("view_count"))["avg"] or 0,
                "top_recipe": yearly_recipes.first(),
            }
        )

    return {
        "year_data": year_data,
        "top_viewed_recipes": top_viewed_recipes,
        "all_recipes": recipes,
        "total_views": total_views,
        "average_views": round(average_views, 1),
        "highest_views": highest_views,
    }


@login_or_guest_required
def dashboard_views_overview(request):
    return render(
        request,
        "yummyrecipes/dashboard/views/views_overview.html",
        views_context(request),
    )


@login_or_guest_required
def dashboard_top_viewed(request):
    return render(
        request,
        "yummyrecipes/dashboard/views/top_viewed.html",
        views_context(request),
    )


@login_or_guest_required
def dashboard_all_views(request):
    return render(
        request,
        "yummyrecipes/dashboard/views/all_views.html",
        views_context(request),
    )


@login_or_guest_required
def dashboard_favourites(request):
    return render(
        request,
        "yummyrecipes/dashboard/favourites/favourites.html",
        favourites_context(request),
    )


def favourites_context(request):
    if request.guest_active:
        return {
            "favourite_recipes": [],
            "total_favourites": 0,
        }

    favourite_recipes = (
        post.objects.filter(favourites=request.user)
        .annotate(
            likes_count=Count("likes", distinct=True),
            view_count=Sum("hit_count_generic__hits"),
        )
        .order_by("-date_modified")
    )

    return {
        "favourite_recipes": favourite_recipes,
        "total_favourites": favourite_recipes.count(),
    }


@login_or_guest_required
def dashboard_network(request):
    return render(
        request,
        "yummyrecipes/dashboard/network/network.html",
        network_context(request),
    )


def network_context(request):
    if request.guest_active:
        return {
            "followers_count": 0,
            "following_count": 0,
            "year_data": [],
        }

    user = request.user

    followers = Follow.objects.filter(following=user).select_related("follower").order_by("-created_at")

    following = Follow.objects.filter(follower=user).select_related("following").order_by("-created_at")

    follower_years = followers.dates("created_at", "year")
    following_years = following.dates("created_at", "year")

    years = sorted(
        set(chain(follower_years, following_years)),
        reverse=True,
    )

    year_data = []

    for year in years:
        follower_qs = followers.filter(created_at__year=year.year)

        following_qs = following.filter(created_at__year=year.year)

        year_data.append(
            {
                "year": year.year,
                "followers": follower_qs,
                "following": following_qs,
                "followers_count": follower_qs.count(),
                "following_count": following_qs.count(),
            }
        )

    return {
        "followers_count": followers.count(),
        "following_count": following.count(),
        "year_data": year_data,
    }


@login_or_guest_required
def dashboard_network_followers(request, year):
    context = network_context(request)

    selected = next(
        (item for item in context["year_data"] if item["year"] == year),
        None,
    )

    return render(
        request,
        "yummyrecipes/dashboard/network/followers.html",
        {
            "year": year,
            "followers": (selected["followers"] if selected else []),
        },
    )


@login_or_guest_required
def dashboard_network_following(request, year):
    context = network_context(request)

    selected = next(
        (item for item in context["year_data"] if item["year"] == year),
        None,
    )

    return render(
        request,
        "yummyrecipes/dashboard/network/following.html",
        {
            "year": year,
            "following": (selected["following"] if selected else []),
        },
    )


@login_required(login_url="login")
def feedback_view(request):
    try:
        if request.method == "POST":
            form = FeedbackForm(request.POST)
            if form.is_valid():
                feedback = form.save(commit=False)
                feedback.user = request.user
                feedback.save()
                messages.success(request, "Feedback submitted", extra_tags="feedback")

                return redirect("feedback")
        else:
            form = FeedbackForm()

        user_feedback = Feedback.objects.filter(user=request.user)
        feedback_len = Feedback.objects.filter(user=request.user).count()
        return render(
            request,
            "yummyrecipes/feedback_form.html",
            {
                "form": form,
                "user_feedback": user_feedback,
                "feedback_len": feedback_len,
            },
        )
    except Exception as e:
        error = str(e)
        return render(request, "yummyrecipes/feedback_form.html", {"error_message": error})


@login_required
def follow_unfollow_user(request, username):
    target_user = get_object_or_404(User, username=username)

    if request.user == target_user:
        return JsonResponse(
            {
                "success": False,
                "message": "Action not allowed",
            }
        )

    followed = False

    if Follow.objects.filter(follower=request.user, following=target_user).exists():
        Follow.objects.filter(
            follower=request.user,
            following=target_user,
        ).delete()

        Notification.objects.filter(
            actor_object_id=request.user.id,
            recipient=target_user,
            verb="following",
        ).delete()

        action = "unfollow"

    else:
        Follow.objects.create(
            follower=request.user,
            following=target_user,
        )

        notify.send(
            sender=request.user,
            recipient=target_user,
            verb="following",
        )

        followed = True
        action = "follow"

    followers_count = Follow.objects.filter(following=target_user).count()

    following_count = Follow.objects.filter(follower=target_user).count()

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "action": action,
                "followers": followers_count,
                "following": following_count,
            }
        )

    if followed:
        messages.success(
            request,
            f"{target_user.get_full_name()}",
            extra_tags="follow_message",
        )

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
