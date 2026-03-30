from django.conf import settings
from django.db import models


NOTIFICATION_TYPES = [
    ("new_message", "New Message"),
    ("booking_request", "Booking Request"),
    ("booking_accepted", "Booking Accepted"),
    ("booking_declined", "Booking Declined"),
    ("booking_completed", "Booking Completed"),
    ("item_sold", "Item Marked as Sold"),
    ("new_review", "New Review Received"),
    ("listing_reported", "Listing Reported"),
    ("account_verified", "Account Verified"),
    ("price_drop", "Price Drop on Saved Item"),
    ("pro_activated", "Pro Subscription Activated"),
    ("pro_expired", "Pro Subscription Expired"),
    ("payment_rejected", "Payment Rejected"),
]


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    action_url = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} → {self.user}"

    @classmethod
    def create(cls, user, notification_type, title, message, action_url=""):
        """Convenience factory method to create a Notification instance."""
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
        )
