import calendar
import datetime
from datetime import date

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
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


def overview_context(request):
    user = request.user

    if request.guest_active:
        return {
            "tot_posts_byuser": 0,
            "breakfast": 0,
            "lunch": 0,
            "evesnack": 0,
            "dinner": 0,
            "veg": 0,
            "nonveg": 0,
            "last_recipe": None,
            "last_viewed_recipe": None,
            "last_comment": None,
            "commented_post": None,
            "last_liked_recipe": None,
            "total_views": 0,
        }

    last_comment = (
        comments.objects.filter(comment_user=user)
        .select_related("post_super")
        .prefetch_related("post_super__photo_set")
        .order_by("-date_comment")
        .first()
    )

    return {
        "tot_posts_byuser": post.objects.filter(author=user).count(),
        "breakfast": post.objects.filter(author=user, type="Breakfast").count(),
        "lunch": post.objects.filter(author=user, type="Lunch").count(),
        "evesnack": post.objects.filter(author=user, type="Evening Snack").count(),
        "dinner": post.objects.filter(author=user, type="Dinner").count(),
        "veg": post.objects.filter(author=user, category="Veg").count(),
        "nonveg": post.objects.filter(author=user, category="Non-Veg").count(),
        "last_recipe": post.objects.filter(author=user).prefetch_related("photo_set").last(),
        "last_viewed_recipe": BlogHistory.objects.filter(user=user)
        .select_related("blog_post")
        .prefetch_related("blog_post__photo_set")
        .order_by("-timestamp")
        .first(),
        "last_comment": last_comment,
        "commented_post": last_comment.post_super if last_comment else None,
        "last_liked_recipe": post.objects.filter(likes=user.profile).prefetch_related("photo_set").order_by("-date_modified").first(),
        "total_views": post.objects.filter(author=user).aggregate(total=Sum("hit_count_generic__hits"))["total"] or 0,
    }


def my_recipes_context(request):
    user = request.user

    if request.guest_active:
        return {
            "top_performing_recipes": None,
            "update_recipe_text": None,
            "goal_for_year": 0,
            "progress_percentage": 0,
            "recipes_uploaded": 0,
            "types": [],
            "category_dict": {},
        }

    types = [
        "All",
        "Breakfast",
        "Lunch",
        "Evening Snack",
        "Dinner",
        "Veg",
        "Non-Veg",
    ]

    category_dict = {"All": post.objects.filter(author=user).order_by("-date_post")}

    for category in types[1:]:
        category_dict[category] = (
            post.objects.filter(author=user).filter(Q(type__iexact=category) | Q(category__iexact=category)).order_by("-date_post")
        )

    current_year = date.today().year

    goal = YearlyGoal.objects.filter(profile=user.profile, year=current_year).first()

    goal_value = goal.goal if goal else 0

    recipes_uploaded = post.objects.filter(author=user, date_post__year=current_year).count()

    progress = recipes_uploaded / goal_value * 100 if goal_value else 0

    return {
        "top_performing_recipes": post.top_performing_recipes(user),
        "update_recipe_text": request.session.pop("update_recipe_message", None),
        "recipes_uploaded": recipes_uploaded,
        "goal_for_year": goal,
        "progress_percentage": int(progress),
        "types": types,
        "category_dict": category_dict,
    }


@login_or_guest_required
def dashboard(request):
    active_tab = request.GET.get("tab", "overview")

    tab_urls = {
        "overview": "dashboard_overview",
        "my-recipes": "dashboard_my_recipes",
        "favorites": "dashboard_favourites",
        "credits": "dashboard_credits",
        "likes": "dashboard_likes",
        "dislikes": "dashboard_dislikes",
        "views": "dashboard_views",
        "timeline": "dashboard_timeline",
        "network": "dashboard_network",
    }

    return render(
        request,
        "yummyrecipes/dashboard.html",
        {
            "active_tab": active_tab,
            "initial_tab_url": tab_urls.get(active_tab, "dashboard_overview"),
        },
    )


@login_or_guest_required
def dashboard_overview(request):
    return render(
        request,
        "yummyrecipes/dashboard/overview.html",
        overview_context(request),
    )


@login_or_guest_required
def dashboard_my_recipes(request):
    context = my_recipes_context(request)

    return render(
        request,
        "yummyrecipes/dashboard/my_recipes.html",
        context,
    )


FILTERS = {
    "breakfast": {"type": "Breakfast"},
    "lunch": {"type": "Lunch"},
    "dinner": {"type": "Dinner"},
    "snack": {"type": "Evening Snack"},
    "veg": {"category": "Veg"},
    "nonveg": {"category": "Non-Veg"},
}


SORTS = {
    "newest": "-date_post",
    "oldest": "date_post",
    "updated": "-date_modified",
    "views": "-views",
    "title_asc": "title",
    "title_desc": "-title",
}


def dashboard_queryset(request):
    queryset = post.objects.filter(author=request.user)

    # Filter
    filter_by = request.GET.get("filter", "all")

    if filter_by in FILTERS:
        queryset = queryset.filter(**FILTERS[filter_by])

    # Sort
    sort = request.GET.get("sort", "newest")

    if sort == "likes":
        queryset = queryset.annotate(likes_count=Count("likes", distinct=True)).order_by("-likes_count", "-date_post")

    else:
        queryset = queryset.order_by(SORTS.get(sort, "-date_post"))

    return queryset, filter_by, sort


PAGE_SIZE = 12


@login_or_guest_required
def dashboard_recipe_list(request):
    queryset, filter_by, sort = dashboard_queryset(request)

    paginator = Paginator(queryset, PAGE_SIZE)

    page_obj = paginator.get_page(1)

    return render(
        request,
        "yummyrecipes/dashboard/recipe_list_partial.html",
        {
            "posts": page_obj,
            "current_filter": filter_by,
            "current_sort": sort,
        },
    )


@login_or_guest_required
def dashboard_recipe_cards(request):
    """
    Load More endpoint.
    Returns only recipe cards.
    """

    queryset, filter_by, sort = dashboard_queryset(request)

    paginator = Paginator(queryset, PAGE_SIZE)

    page_number = request.GET.get("page", 1)

    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "yummyrecipes/dashboard/recipe_cards_oob_partial.html",
        {
            "posts": page_obj,
            "current_filter": filter_by,
            "current_sort": sort,
        },
    )


@login_or_guest_required
def dashboard_timeline(request):
    return render(
        request,
        "yummyrecipes/dashboard/timeline/timeline.html",
        timeline_context(request),
    )


def timeline_context(request):
    if request.guest_active:
        return {
            "year_data": [],
            "recent_uploads": [],
            "total_recipes": 0,
            "years_active": 0,
            "best_year": None,
        }

    user = request.user

    recipes = (
        post.objects.filter(author=user)
        .annotate(
            likes_count=Count("likes", distinct=True),
            view_count=Sum("hit_count_generic__hits"),
        )
        .order_by("-date_post")
    )

    total_recipes = recipes.count()

    current_year = datetime.date.today().year
    joined_year = user.date_joined.year

    years = list(range(current_year, joined_year - 1, -1))

    year_data = []

    best_year = None
    best_count = 0

    for year in years:
        yearly_recipes = recipes.filter(date_post__year=year)

        monthly = yearly_recipes.annotate(month=ExtractMonth("date_post")).values("month").annotate(total=Count("id")).order_by("month")

        month_counts = {m: 0 for m in range(1, 13)}

        for row in monthly:
            month_counts[row["month"]] = row["total"]

        max_month = max(month_counts.values()) or 1

        yearly_total = yearly_recipes.count()

        if yearly_total > best_count:
            best_count = yearly_total
            best_year = year

        # Best month
        if month_counts:
            best_month_num = max(month_counts, key=month_counts.get)
        else:
            best_month_num = 1

        top_recipe = yearly_recipes.order_by("-view_count").first()

        months = []

        for month in range(1, 13):
            month_recipes = yearly_recipes.filter(date_post__month=month).order_by("-date_post")

            months.append(
                {
                    "number": month,
                    "name": calendar.month_name[month],
                    "count": month_recipes.count(),
                    "recipes": month_recipes,
                }
            )

        year_data.append(
            {
                "year": year,
                "total": yearly_total,
                "max_month": max_month,
                "best_month": calendar.month_name[best_month_num],
                "top_recipe": top_recipe,
                "months": months,
            }
        )

    recent_uploads = recipes[:10]

    return {
        "year_data": year_data,
        "recent_uploads": recent_uploads,
        "total_recipes": total_recipes,
        "years_active": len(years),
        "best_year": best_year,
    }


@login_or_guest_required
def dashboard_timeline_overview(request):
    return render(
        request,
        "yummyrecipes/dashboard/timeline/overview.html",
        timeline_context(request),
    )


@login_or_guest_required
def dashboard_publishing_history(request):
    return render(
        request,
        "yummyrecipes/dashboard/timeline/publishing_history.html",
        timeline_context(request),
    )


@login_or_guest_required
def dashboard_recent_uploads(request):
    return render(
        request,
        "yummyrecipes/dashboard/timeline/recent_uploads.html",
        timeline_context(request),
    )


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
        "yummyrecipes/year_recap.html",
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
