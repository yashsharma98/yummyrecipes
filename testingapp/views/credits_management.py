import calendar
import json
from calendar import month_name

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.db.models.functions import ExtractMonth, TruncMonth
from django.http import (
    HttpResponseForbidden,
)
from django.shortcuts import redirect, render

from ..models import (
    CreditHistory,
    CreditSpentHistory,
    RedeemedCredit,
)


@login_required(login_url="login")
# @login_or_guest_required
def credits(request):
    if not request.guest_active:
        user = request.user
        profile = user.profile

        if request.method == "POST":
            redeem_amount = int(request.POST.get("redeem_amount", 0))

            # Ensure the redeem amount is not greater than the earned credits
            redeem_amount = min(redeem_amount, profile.earned_credits)

            # Add the redeem amount to the credits field
            profile.credits += redeem_amount

            # Add the redeemed credits to the redeemed_credits field
            profile.redeemed_credits += redeem_amount

            # redeemed_credit = RedeemedCredit.objects.create(user=user, amount=redeem_amount)

            profile.earned_credits -= redeem_amount

            profile.save()

            return redirect("credits")

        redeemed_credits = RedeemedCredit.objects.filter(user=user)

        credit_history = CreditHistory.objects.filter(user=user)

        credit_spent_history = CreditSpentHistory.objects.filter(user=user)

        credit_spent_by_month = (
            credit_spent_history.annotate(month=TruncMonth("spent_timestamp")).values("month").annotate(total_credits_spent=Sum("amount"))
        )

        # Calculate the total number of months for which there are credit spent records
        total_months = credit_spent_by_month.count()

        total_credits_spent = sum(entry["total_credits_spent"] for entry in credit_spent_by_month)

        if total_months > 0:
            average_credit_spent = total_credits_spent / total_months
        else:
            average_credit_spent = 0

        credit_spent_by_month = (
            CreditSpentHistory.objects.filter(user=user)
            .annotate(month=ExtractMonth("spent_timestamp"))
            .values("month")
            .annotate(total_credits_spent=Sum("amount"))
        )

        average_credit_spent_month = CreditSpentHistory.objects.filter(user=user).aggregate(avg_credit_spent=Avg("amount"))["avg_credit_spent"]

        credit_spent_by_month_json = json.dumps(list(credit_spent_by_month))
        average_credit_spent_json = json.dumps(average_credit_spent_month)

        monthly_summary = {}

        earned_by_month = (
            CreditHistory.objects.filter(user=user, credit_action="new_recipe")
            .annotate(month=ExtractMonth("earned_timestamp"))
            .values("month")
            .annotate(total_earned=Sum("amount"))
        )

        spent_by_month = (
            CreditSpentHistory.objects.filter(user=user)
            .annotate(month=ExtractMonth("spent_timestamp"))
            .values("month")
            .annotate(total_spent=Sum("amount"))
        )

        redeemed_by_month = (
            RedeemedCredit.objects.filter(user=user)
            .annotate(month=ExtractMonth("redeemed_timestamp"))
            .values("month")
            .annotate(total_redeemed=Sum("amount"))
        )

        for month in range(1, 13):
            monthly_summary[month_name[month]] = {
                "earned": 0,
                "spent": 0,
                "redeemed": 0,
            }

        for entry in earned_by_month:
            month = calendar.month_name[entry["month"]]
            monthly_summary.setdefault(month, {"earned": 0, "spent": 0, "redeemed": 0})
            monthly_summary[month]["earned"] = entry["total_earned"]

        for entry in spent_by_month:
            month = calendar.month_name[entry["month"]]
            monthly_summary.setdefault(month, {"earned": 0, "spent": 0, "redeemed": 0})
            monthly_summary[month]["spent"] = entry["total_spent"]

        for entry in redeemed_by_month:
            month = calendar.month_name[entry["month"]]
            monthly_summary.setdefault(month, {"earned": 0, "spent": 0, "redeemed": 0})
            monthly_summary[month]["redeemed"] = entry["total_redeemed"]

        monthly_summary_list = [
            {
                "month": month,
                "earned": values["earned"],
                "spent": values["spent"],
                "redeemed": values["redeemed"],
            }
            for month, values in sorted(
                monthly_summary.items(),
                key=lambda x: list(calendar.month_name).index(x[0]),
            )
        ]

        return render(
            request,
            "testingapp/credits.html",
            {
                "redeemed_credits": redeemed_credits,
                "credit_history": credit_history,
                "credit_spent_history": credit_spent_history,
                "total_credits_spent": total_credits_spent,
                "average_credit_spent": average_credit_spent,
                "credit_spent_by_month_json": credit_spent_by_month_json,
                "average_credit_spent_json": average_credit_spent_json,
                "monthly_summary_list": monthly_summary_list,
            },
        )

    else:
        return render(request, "testingapp/credits.html")
        # return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


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
