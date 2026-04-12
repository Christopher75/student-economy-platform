from django.utils import timezone
from django.shortcuts import redirect
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
        response = self.get_response(request)
        if request.user.is_authenticated:
            now = timezone.now()
            last_seen = request.user.last_seen
            should_update = (
                last_seen is None
                or (now - last_seen) > self.UPDATE_INTERVAL
            )
            if should_update:
                request.user.last_seen = now
                request.user.save(update_fields=['last_seen'])
        return response


# URL prefixes that are exempt from the email-verification gate
_EXEMPT_PREFIXES = (
    '/accounts/verify-email',   # OTP page and legacy token page
    '/accounts/resend-otp',
    '/accounts/logout',
    '/accounts/login',
    '/accounts/register',
    '/accounts/password-reset',
    '/static/',
    '/media/',
    '/favicon',
)
_EXEMPT_EXACT = ('/',)


class EmailVerificationMiddleware:
    """
    Redirect authenticated users who have not yet verified their email to the
    OTP verification page. All URL prefixes in _EXEMPT_PREFIXES are allowed through.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and not request.user.is_email_verified
            and not self._is_exempt(request.path)
        ):
            return redirect('/accounts/verify-email/')
        return self.get_response(request)

    @staticmethod
    def _is_exempt(path):
        if path in _EXEMPT_EXACT:
            return True
        for prefix in _EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return True
        return False
