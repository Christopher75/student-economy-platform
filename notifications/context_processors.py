def notifications_processor(request):
    if request.user.is_authenticated:
        try:
            from notifications.models import Notification
            unread = Notification.objects.filter(user=request.user, is_read=False).count()
            recent = Notification.objects.filter(user=request.user)[:5]
            return {"unread_notifications_count": unread, "recent_notifications": recent}
        except Exception:
            pass
    return {"unread_notifications_count": 0, "recent_notifications": []}
