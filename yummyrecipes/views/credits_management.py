from calendar import month_name

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.db.models.functions import ExtractMonth
from django.http import (
    HttpResponseForbidden,
)
from django.shortcuts import redirect, render

from ..decorators import login_or_guest_required
from ..models import (
    CreditHistory,
    CreditSpentHistory,
    RedeemedCredit,
)


@login_required(login_url="login")
def credits(request):
    return render(request, "yummyrecipes/dashboard/credits/credits.html")
    # return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


def get_credits_context(request):
    user = request.user

    if request.guest_active:
        return {
            "current_balance": 0,
            "earned_credits": 0,
            "redeemed_total": 0,
            "monthly_summary_list": [],
            "credit_history": [],
            "credit_spent_history": [],
            "redeemed_credits": [],
            "average_credit_spent": 0,
            "total_credits_spent": 0,
        }

    profile = user.profile

    redeemed_credits = RedeemedCredit.objects.filter(user=user).order_by("-redeemed_timestamp")

    credit_history = CreditHistory.objects.filter(user=user).order_by("-earned_timestamp")

    credit_spent_history = CreditSpentHistory.objects.filter(user=user).order_by("-spent_timestamp")

    # ---------- Monthly Summary ----------

    monthly_summary = {
        month_name[m]: {
            "earned": 0,
            "spent": 0,
            "redeemed": 0,
        }
        for m in range(1, 13)
    }

    earned = CreditHistory.objects.filter(user=user).annotate(month=ExtractMonth("earned_timestamp")).values("month").annotate(total=Sum("amount"))

    spent = CreditSpentHistory.objects.filter(user=user).annotate(month=ExtractMonth("spent_timestamp")).values("month").annotate(total=Sum("amount"))

    redeemed = (
        RedeemedCredit.objects.filter(user=user).annotate(month=ExtractMonth("redeemed_timestamp")).values("month").annotate(total=Sum("amount"))
    )

    for item in earned:
        monthly_summary[month_name[item["month"]]]["earned"] = item["total"]

    for item in spent:
        monthly_summary[month_name[item["month"]]]["spent"] = item["total"]

    for item in redeemed:
        monthly_summary[month_name[item["month"]]]["redeemed"] = item["total"]

    monthly_summary_list = [
        {
            "month": month,
            **values,
        }
        for month, values in monthly_summary.items()
    ]

    total_credits_spent = credit_spent_history.aggregate(total=Sum("amount"))["total"] or 0

    average_credit_spent = credit_spent_history.aggregate(avg=Avg("amount"))["avg"] or 0

    return {
        "current_balance": profile.credits,
        "earned_credits": profile.earned_credits,
        "redeemed_total": profile.redeemed_credits,
        "redeemed_credits": redeemed_credits,
        "credit_history": credit_history,
        "credit_spent_history": credit_spent_history,
        "monthly_summary_list": monthly_summary_list,
        "total_credits_spent": total_credits_spent,
        "average_credit_spent": round(average_credit_spent, 1),
    }


@login_or_guest_required
def dashboard_credits(request):
    return render(
        request,
        "yummyrecipes/dashboard/credits/credits.html",
        get_credits_context(request),
    )


@login_or_guest_required
def dashboard_credit_monthly(request):
    return render(
        request,
        "yummyrecipes/dashboard/credits/credit_monthly.html",
        get_credits_context(request),
    )


@login_or_guest_required
def dashboard_redeem_credit(request):
    if request.method != "POST":
        return HttpResponseForbidden()

    if request.guest_active:
        return HttpResponseForbidden()

    profile = request.user.profile

    try:
        redeem_amount = int(request.POST.get("redeem_amount", 0))
    except ValueError:
        redeem_amount = 0

    redeem_amount = max(0, redeem_amount)
    redeem_amount = min(redeem_amount, profile.earned_credits)

    if redeem_amount:
        profile.credits += redeem_amount
        profile.redeemed_credits += redeem_amount
        profile.earned_credits -= redeem_amount

        profile.save()

        RedeemedCredit.objects.create(
            user=request.user,
            amount=redeem_amount,
        )

    return render(
        request,
        "yummyrecipes/dashboard/credits/credits.html",
        get_credits_context(request),
    )


@login_or_guest_required
def dashboard_credit_earned(request):
    return render(
        request,
        "yummyrecipes/dashboard/credits/earned.html",
        get_credits_context(request),
    )


@login_or_guest_required
def dashboard_credit_redeemed(request):
    return render(
        request,
        "yummyrecipes/dashboard/credits/redeemed.html",
        get_credits_context(request),
    )


@login_or_guest_required
def dashboard_credit_spent(request):
    return render(
        request,
        "yummyrecipes/dashboard/credits/spent.html",
        get_credits_context(request),
    )


@login_required(login_url="login")
def delete_redeemed_history(request):
    if request.method == "POST":
        redeemed_history_ids = request.POST.getlist("redeemed_history")
        RedeemedCredit.objects.filter(id__in=redeemed_history_ids, user=request.user).delete()
        return redirect("credits")
    else:
        return HttpResponseForbidden("Unable to perform this action.")


@login_required(login_url="login")
def delete_credit_history(request):
    if request.method == "POST":
        selected_ids = request.POST.getlist("selected_history")
        CreditHistory.objects.filter(id__in=selected_ids, user=request.user).delete()
        return redirect("credits")
    else:
        return HttpResponseForbidden("Unable to perform this action.")


@login_required(login_url="login")
def delete_spent_history(request):
    if request.method == "POST":
        spent_history_ids = request.POST.getlist("spent_history")
        CreditSpentHistory.objects.filter(id__in=spent_history_ids, user=request.user).delete()
        return redirect("credits")
    else:
        return HttpResponseForbidden("Unable to perform this action.")
