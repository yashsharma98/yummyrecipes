import calendar
from collections import OrderedDict
from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Max, Sum
from django.http import (
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from notifications.models import Notification
from notifications.signals import notify

from ..forms import (
    FeedbackForm,
)
from ..models import (
    Feedback,
    Follow,
    post,
    profile,
)
from ..utils.history_helpers import get_historys_pk


@login_required(login_url="login")
def liked_recipes(request):
    if not request.guest_active:
        user = request.user

        all_liked_recipes = post.objects.filter(likes__user=request.user).annotate(num_likes=Count("likes")).order_by("-num_likes")
        total_likes = post.objects.filter(likes__user=request.user).count()

        recipes_with_likes = (
            post.objects.filter(author=request.user, likes__isnull=False).annotate(num_likes=Count("likes")).order_by("-num_likes").distinct()
        )
        total_recipes_with_likes = post.objects.filter(author=request.user, likes__isnull=False).distinct().count()

        top_liked_recipe = post.objects.filter(author=user).annotate(num_likes=Count("likes")).order_by("-num_likes")[0:1]
        top_likes = post.objects.filter(author=request.user).annotate(num_likes=Count("likes")).aggregate(most_likes=Max("num_likes"))["most_likes"]

        if top_likes is None:
            top_likes = 0

        return render(
            request,
            "testingapp/liked_recipes.html",
            {
                "all_liked_recipes": all_liked_recipes,
                "total_likes": total_likes,
                "recipes_with_likes": recipes_with_likes,
                "total_recipes_with_likes": total_recipes_with_likes,
                "top_liked_recipe": top_liked_recipe,
                "top_likes": top_likes,
                "historys_pk": get_historys_pk(request.user),
            },
        )

    else:
        return render(request, "testingapp/liked_recipes.html")


@login_required(login_url="login")
def disliked_recipes(request):
    if not request.guest_active:
        user = request.user

        all_disliked_recipes = post.objects.filter(dislikes__user=request.user).annotate(num_dislikes=Count("dislikes")).order_by("-num_dislikes")
        total_dislikes = post.objects.filter(dislikes__user=request.user).count()

        recipes_with_dislikes = (
            post.objects.filter(author=request.user, dislikes__isnull=False)
            .annotate(num_dislikes=Count("dislikes"))
            .order_by("-num_dislikes")
            .distinct()
        )
        total_recipes_with_dislikes = post.objects.filter(author=request.user, dislikes__isnull=False).distinct().count()

        top_disliked_recipe = post.objects.filter(author=user).annotate(num_dislikes=Count("dislikes")).order_by("-num_dislikes")[0:1]
        top_dislikes = (
            post.objects.filter(author=request.user)
            .annotate(num_dislikes=Count("dislikes"))
            .aggregate(most_dislikes=Max("num_dislikes"))["most_dislikes"]
        )

        if top_dislikes is None:
            top_dislikes = 0

        return render(
            request,
            "testingapp/disliked_recipes.html",
            {
                "all_disliked_recipes": all_disliked_recipes,
                "total_dislikes": total_dislikes,
                "recipes_with_dislikes": recipes_with_dislikes,
                "total_recipes_with_dislikes": total_recipes_with_dislikes,
                "top_disliked_recipe": top_disliked_recipe,
                "top_dislikes": top_dislikes,
                "historys_pk": get_historys_pk(request.user),
            },
        )

    else:
        return render(request, "testingapp/disliked_recipes.html")


@login_required(login_url="login")
def total_views(request):
    if not request.guest_active:
        user = request.user
        posts = post.objects.filter(author=user)

        distinct_years = post.objects.filter(author=user).dates("date_post", "year").reverse()

        year_recipes = {}
        year_hits = {}
        avg_hits = {}
        most_hit = {}

        for year in distinct_years:
            recipes_for_year = post.objects.filter(author=user, date_post__year=year.year)
            year_recipes[year.year] = recipes_for_year

            total_hits_per_year = post.objects.filter(author=user, date_post__year=year.year).aggregate(total=Sum("hit_count_generic__hits"))["total"]
            year_hits[year.year] = total_hits_per_year

            total_hits_avg = post.objects.filter(author=user, date_post__year=year.year).aggregate(total=Avg("hit_count_generic__hits"))["total"]
            avg_hits[year.year] = total_hits_avg

            top_hit = post.objects.filter(author=user, date_post__year=year.year).order_by("-hit_count_generic__hits").first()
            most_hit[year.year] = top_hit

        return render(
            request,
            "testingapp/total_views.html",
            {
                "distinct_years": distinct_years,
                "year_recipes": year_recipes,
                "year_hits": year_hits,
                "avg_hits": avg_hits,
                "most_hit": most_hit,
                "posts": posts,
            },
        )

    else:
        return render(request, "testingapp/total_views.html")


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
            "testingapp/feedback_form.html",
            {
                "form": form,
                "user_feedback": user_feedback,
                "feedback_len": feedback_len,
            },
        )
    except Exception as e:
        error = str(e)
        return render(request, "testingapp/feedback_form.html", {"error_message": error})


@login_required
def follow_unfollow_user(request, username):
    target_user = get_object_or_404(User, username=username)
    current_user_profile = profile.objects.get(user=request.user)  # noqa: F841
    followed = False
    authenticated_user = False

    if request.user != target_user:
        # if user is following the targered user
        if Follow.objects.filter(follower=request.user, following=target_user).exists():
            # Then unfollow the targeted user
            Follow.objects.filter(follower=request.user, following=target_user).delete()

            # Delete the following notification
            Notification.objects.filter(actor_object_id=request.user.id, recipient=target_user, verb="following").delete()
        else:
            # Follow the targeted user
            Follow.objects.create(follower=request.user, following=target_user)
            followed = True

            notify.send(
                sender=request.user,
                recipient=target_user,
                verb="following",
            )
    else:
        authenticated_user = True

    if followed:
        messages.success(request, f"{target_user.get_full_name()}", extra_tags="follow_message")

    if authenticated_user:
        messages.success(request, "Action not allowed", extra_tags="same_user")

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required(login_url="login")
def followers_list(request, name, pk):
    if not request.guest_active:
        user = request.user
        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()

        followers = Follow.objects.filter(following=user)
        following = Follow.objects.filter(follower=user)

        follower_years_qs = Follow.objects.filter(following=user).dates("created_at", "year")
        following_years_qs = Follow.objects.filter(follower=user).dates("created_at", "year")
        distinct_years = sorted(set(chain(follower_years_qs, following_years_qs)), reverse=True)

        year_data = {}
        year_data_history = OrderedDict()

        for year in distinct_years:
            year_int = year.year
            followers_for_year = Follow.objects.filter(following=user, created_at__year=year_int)
            followings_for_year = Follow.objects.filter(follower=user, created_at__year=year_int)

            year_data[year_int] = {
                "followers": followers_for_year,
                "followings": followings_for_year,
            }

            year_data_history[year_int] = {}

            for month in range(1, 13):
                month_name = calendar.month_name[month]

                followers_for_month = Follow.objects.filter(following=user, created_at__year=year_int, created_at__month=month)
                followings_for_month = Follow.objects.filter(follower=user, created_at__year=year_int, created_at__month=month)
                total_followers_count = Follow.objects.filter(following=user, created_at__year=year_int).count()
                total_followings_count = Follow.objects.filter(follower=user, created_at__year=year_int).count()

                if followers_for_month.exists() or followings_for_month.exists():
                    year_data_history[year_int][month_name] = {
                        "followers": followers_for_month,
                        "followings": followings_for_month,
                        "followers_obj": followers_for_year,
                        "followings_obj": followings_for_year,
                        "monthly_followers_count": total_followers_count,
                        "monthly_followings_count": total_followings_count,
                    }
                else:
                    year_data_history[year_int][month_name] = {
                        "followers": "",
                        "followings": "",
                        "followers_obj": "",
                        "followings_obj": "",
                    }

        return render(
            request,
            "testingapp/connections.html",
            {
                "user": user,
                "followers": followers,
                "following": following,
                "followers_count": followers_count,
                "following_count": following_count,
                "distinct_years": distinct_years,
                "year_data": year_data,
                "year_data_history": year_data_history,
            },
        )

    else:
        return render(request, "testingapp/connections.html")


@login_required(login_url="login")
def favorite_list(request):
    new = post.objects.filter(favourites=request.user)
    return render(request, "testingapp/favourites.html", {"new": new})
