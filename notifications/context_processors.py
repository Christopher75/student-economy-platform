def notifications_processor(request):
    if request.user.is_authenticated:
        from notifications.models import Notification
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        recent = Notification.objects.filter(user=request.user)[:5]
        return {"unread_notifications_count": unread, "recent_notifications": recent}
    return {"unread_notifications_count": 0, "recent_notifications": []}
