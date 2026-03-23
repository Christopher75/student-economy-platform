def unread_messages_processor(request):
    if request.user.is_authenticated:
        from messaging.models import Message
        count = Message.objects.filter(
            conversation__participants=request.user,
            read_at__isnull=True,
        ).exclude(sender=request.user).count()
        return {"unread_messages_count": count}
    return {"unread_messages_count": 0}
