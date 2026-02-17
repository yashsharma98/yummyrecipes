import calendar
import datetime
import json
from collections import defaultdict
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth
from django.shortcuts import redirect, render

from ..decorators import login_or_guest_required
from ..forms import (
    YearlyGoal,
)
from ..models import (
    BlogHistory,
    comments,
    post,
)


# @login_required(login_url='login')
@login_or_guest_required
def dashboard(request):
    user = request.user

    if not request.guest_active:
        category_dict = {}
        types = [
            "All",
            "Breakfast",
            "Lunch",
            "Evening Snack",
            "Dinner",
            "Veg",
            "Non-Veg",
        ]

        all_posts = post.objects.filter(author=user).order_by("-date_post")
        category_dict["All"] = all_posts

        for category in types[1:]:
            category_posts = post.objects.filter(author=user).filter(Q(type__iexact=category) | Q(category__iexact=category)).order_by("-date_post")

            category_dict[category] = category_posts

        tot_posts_byuser = post.objects.filter(author=user).all().count()
        breakfast = post.objects.filter(author=request.user, type="Breakfast").count()
        lunch = post.objects.filter(author=request.user, type="Lunch").count()
        evesnack = post.objects.filter(author=request.user, type="Evening Snack").count()
        dinner = post.objects.filter(author=request.user, type="Dinner").count()
        veg = post.objects.filter(author=request.user, category="Veg").count()
        nonveg = post.objects.filter(author=request.user, category="Non-Veg").count()

        last_recipe = post.objects.filter(author=request.user).last()

        last_viewed_recipe = BlogHistory.objects.filter(user=request.user).order_by("-timestamp").first()

        last_comment = comments.objects.filter(comment_user=request.user).order_by("-date_comment").first()

        if last_comment:
            commented_post = last_comment.post_super
        else:
            commented_post = ""

        top_performing_recipes = post.top_performing_recipes(request.user)

        last_liked_recipe = post.objects.filter(likes=user.profile).order_by("-date_modified").first()

        # success message for updating the recipe
        update_recipe_text = request.session.pop("update_recipe_message", None)

        current_year = date.today().year

        user_profile = request.user.profile

        recipes_uploaded = post.objects.filter(author=request.user, date_post__year=current_year).count()

        # goals set for current year
        goal_for_year = YearlyGoal.objects.filter(profile=user_profile, year=current_year).first()
        goal_for_year_value = goal_for_year.goal if goal_for_year else 0

        # recipes uploaded in current year not counting the previous years recipes
        recipes_uploaded = post.objects.filter(author=request.user, date_post__year=current_year).count()

        # Calculating progress percentage
        progress_percentage = (recipes_uploaded / goal_for_year_value) * 100 if goal_for_year_value > 0 else 0

    else:
        category_dict = {}
        types = [
            "All",
            "Breakfast",
            "Lunch",
            "Evening Snack",
            "Dinner",
            "Veg",
            "Non-Veg",
        ]
        tot_posts_byuser, breakfast, lunch, evesnack, dinner, veg, nonveg = (
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        )
        (
            last_recipe,
            last_viewed_recipe,
            last_comment,
            commented_post,
            last_liked_recipe,
        ) = None, None, None, None, None
        top_performing_recipes, update_recipe_text, recipes_uploaded = None, None, None
        goal_for_year, progress_percentage = 0, 0

    return render(
        request,
        "testingapp/dashboard.html",
        {
            "tot_posts_byuser": tot_posts_byuser,
            "breakfast": breakfast,
            "lunch": lunch,
            "evesnack": evesnack,
            "dinner": dinner,
            "veg": veg,
            "nonveg": nonveg,
            "last_recipe": last_recipe,
            "last_viewed_recipe": last_viewed_recipe,
            "last_comment": last_comment,
            "commented_post": commented_post,
            "last_liked_recipe": last_liked_recipe,
            "top_performing_recipes": top_performing_recipes,
            "update_recipe_text": update_recipe_text,
            "recipes_uploaded": recipes_uploaded,
            "goal_for_year": goal_for_year,
            "progress_percentage": int(progress_percentage),
            "types": types,
            "category_dict": category_dict,
        },
    )


@login_required(login_url="login")
def timeline(request):
    if not request.guest_active:
        user = request.user

        curyear = datetime.datetime.today().year
        joined = user.date_joined.date().year
        year_list = list(range(joined, curyear + 1))

        prev_chart_data_all = {}
        monthly_posts_by_year = defaultdict(lambda: defaultdict(list))
        yearly_recipe_counts = {}
        upcoming_months = defaultdict(lambda: defaultdict(bool))
        today = datetime.date.today()

        category_posts_by_year = defaultdict(lambda: defaultdict(list))
        meal_types = ["Breakfast", "Lunch", "Evening Snack", "Dinner"]

        for year in year_list:
            monthly_recipes = (
                post.objects.filter(author=user, date_post__year=year)
                .annotate(month=ExtractMonth("date_post"))
                .values("month")
                .annotate(recipe_count=Count("id"))
                .order_by("month")
            )

            months = [calendar.month_name[m] for m in range(1, 13)]
            counts = [0] * 12
            for entry in monthly_recipes:
                counts[entry["month"] - 1] = entry["recipe_count"]

            prev_chart_data_all[year] = {"months": months, "recipeCounts": counts}

            for month in range(1, 13):
                monthly_posts = post.objects.filter(author=user, date_post__year=year, date_post__month=month).order_by("-date_post")
                monthly_posts_by_year[year][month] = list(monthly_posts)

                if year > today.year or (year == today.year and month > today.month):
                    upcoming_months[year][month] = True
                else:
                    upcoming_months[year][month] = False

            yearly_recipe_counts[year] = post.objects.filter(author=user, date_post__year=year).count()

            for category in meal_types:
                category_posts = post.objects.filter(author=user, date_post__year=year, type__iexact=category).order_by("-hit_count_generic__hits")
                category_posts_by_year[year][category] = list(category_posts)

        context = {
            "user": user,
            "year_list": list(reversed(year_list)),
            "curyear": curyear,
            "prev_chart_data_all": json.dumps(prev_chart_data_all),
            "monthly_posts_by_year": monthly_posts_by_year,
            "yearly_recipe_counts": yearly_recipe_counts,
            "month_range": range(1, 13),
            "today": today,
            "month_names": dict((i, calendar.month_name[i]) for i in range(1, 13)),
            "upcoming_months": upcoming_months,
            "category_posts_by_year": category_posts_by_year,
            "meal_types": meal_types,
        }

        return render(request, "testingapp/timeline.html", context)

    else:
        return render(request, "testingapp/timeline.html")


@login_required(login_url="login")
def year_recap(request):
    curyear = datetime.datetime.today().year

    user = request.user

    if request.user.is_authenticated:
        auth_trending_recipes = post.objects.filter(author=user, date_post__year=curyear).order_by("-hit_count_generic__hits")

        year_recap = post.objects.filter(author=user, date_post__year=curyear).all()

        total_recipes = post.objects.filter(author=user, date_post__year=curyear).count()
        total_breakfast = post.objects.filter(author=user, type="Breakfast", date_post__year=curyear).count()
        total_lunch = post.objects.filter(author=user, type="Lunch", date_post__year=curyear).count()
        total_evesnack = post.objects.filter(author=user, type="Evening Snack", date_post__year=curyear).count()
        total_dinner = post.objects.filter(author=user, type="Dinner", date_post__year=curyear).count()
        totalveg = post.objects.filter(author=user, category="Veg", date_post__year=curyear).count()
        totalnonveg = post.objects.filter(author=user, category="Non-Veg", date_post__year=curyear).count()

        top_breakfast = post.objects.filter(author=user, type="Breakfast", date_post__year=curyear).order_by("-hit_count_generic__hits")
        top_lunch = post.objects.filter(author=user, type="Lunch", date_post__year=curyear).order_by("-hit_count_generic__hits")
        top_evesnack = post.objects.filter(author=user, type="Evening Snack", date_post__year=curyear).order_by("-hit_count_generic__hits")
        top_dinner = post.objects.filter(author=user, type="Dinner", date_post__year=curyear).order_by("-hit_count_generic__hits")

        topveg = post.objects.filter(author=user, category="Veg", date_post__year=curyear).order_by("-hit_count_generic__hits")
        topnonveg = post.objects.filter(author=user, category="Non-Veg", date_post__year=curyear).order_by("-hit_count_generic__hits")

        most_liked_recipe_count = (
            post.objects.filter(author=request.user, date_post__year=curyear).annotate(like_count=Count("likes")).order_by("-like_count").first()
        )

        most_liked_recipe = (
            post.objects.filter(author=request.user, date_post__year=curyear).annotate(like_count=Count("likes")).order_by("-like_count")
        )

        if most_liked_recipe_count:
            total_likes = most_liked_recipe_count.like_count
        else:
            total_likes = 0

    else:
        return redirect("login")

    return render(
        request,
        "testingapp/year_recap.html",
        {
            "auth_trending_recipes": auth_trending_recipes,
            "year_recap": year_recap,
            "curyear": curyear,
            "total_recipes": total_recipes,
            "top_breakfast": top_breakfast,
            "top_lunch": top_lunch,
            "top_evesnack": top_evesnack,
            "top_dinner": top_dinner,
            "topveg": topveg,
            "topnonveg": topnonveg,
            "most_liked_recipe": most_liked_recipe,
            "total_likes": total_likes,
            "total_breakfast": total_breakfast,
            "total_lunch": total_lunch,
            "total_evesnack": total_evesnack,
            "total_dinner": total_dinner,
            "totalveg": totalveg,
            "totalnonveg": totalnonveg,
        },
    )
