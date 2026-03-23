from django.utils import timezone
from datetime import timedelta


class UpdateLastSeenMiddleware:
    """
    Updates CustomUser.last_seen to the current time on each authenticated
    request. To avoid hammering the database, the field is only saved when
    more than 5 minutes have elapsed since the previous update.
    """

    UPDATE_INTERVAL = timedelta(minutes=5)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request first so auth middleware has already run
        response = self.get_response(request)

        # Only update for authenticated, non-anonymous users
        if request.user.is_authenticated:
            now = timezone.now()
            last_seen = request.user.last_seen

            should_update = (
                last_seen is None
                or (now - last_seen) > self.UPDATE_INTERVAL
            )

            if should_update:
                # Use update_fields to issue a minimal UPDATE statement
                request.user.last_seen = now
                request.user.save(update_fields=['last_seen'])

        return response
