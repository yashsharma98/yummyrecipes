from django.contrib.auth.decorators import login_required
from django.http import (
    JsonResponse,
)
from django.views.decorators.http import require_POST
from notifications.models import Notification


@login_required
@require_POST
def remove_notification(request):
    notification_id = request.POST.get("notification_id")

    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.delete()
        return JsonResponse({"success": True})
    except Notification.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Notification does not exist or you do not have permission to delete it",
            }
        )


# Deleting all notifications for current user
def clear_all_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    return JsonResponse({"message": "All notifications cleared successfully"})
