import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from ..models import (
    BlogHistory,
)


@login_required(login_url="login")
def blog_history(request):
    blog_history = BlogHistory.objects.filter(user=request.user).order_by("-timestamp")
    all = BlogHistory.objects.filter(user=request.user)

    todays_date = datetime.date.today()

    blog_posts = [(entry.pk, entry.blog_post, entry.timestamp) for entry in blog_history]

    todays_date = datetime.date.today()
    yesterday = todays_date - datetime.timedelta(days=1)
    previous_7_days = todays_date - datetime.timedelta(days=7)

    today_posts = [(entry.pk, entry.blog_post, entry.timestamp) for entry in blog_history if entry.timestamp.date() == todays_date]
    yesterday_posts = [(entry.pk, entry.blog_post, entry.timestamp) for entry in blog_history if entry.timestamp.date() == yesterday]
    previous_7_days_posts = [
        (entry.pk, entry.blog_post, entry.timestamp) for entry in blog_history if previous_7_days <= entry.timestamp.date() < todays_date
    ]

    return render(
        request,
        "yummyrecipes/blog_history.html",
        {
            "blog_posts": blog_posts,
            "blog_history": blog_history,
            "all": all,
            "todays_date": todays_date,
            "yesterday": yesterday,
            "previous_7_days": previous_7_days,
            "today_posts": today_posts,
            "yesterday_posts": yesterday_posts,
            "previous_7_days_posts": previous_7_days_posts,
        },
    )


def bulk_delete_blogs(request):
    entry_ids = request.POST.getlist("blog_ids")
    BlogHistory.objects.filter(id__in=entry_ids, user=request.user).delete()
    return redirect("blog_history")


def delete_entry(request, pk):
    if request.method == "POST":
        BlogHistory.objects.filter(pk=pk, user=request.user).delete()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


def delete_all_blog_history(request):
    if request.method == "POST":
        return redirect("blog_history")
    return redirect("blog_history")
