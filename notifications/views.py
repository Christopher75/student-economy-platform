from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """Paginated list of notifications for the current user.

    All unread notifications are marked as read when this view is accessed.
    """

    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        # Mark all unread notifications as read before rendering
        Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return super().get(request, *args, **kwargs)


@login_required
@require_POST
def mark_read(request, pk):
    """Mark a single notification as read. Returns JSON."""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return JsonResponse({"status": "ok", "id": notification.pk})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({"status": "ok"})
    messages.success(request, "All notifications marked as read.")
    return redirect("notifications:notification_list")
