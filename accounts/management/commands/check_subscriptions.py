from datetime import date

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Downgrade expired Pro subscriptions to free and notify users."

    def handle(self, *args, **options):
        today = date.today()
        expired = User.objects.filter(
            subscription_tier="pro",
            subscription_end__lt=today,
        )
        count = expired.count()
        if count == 0:
            self.stdout.write("No expired subscriptions found.")
            return

        for user in expired:
            user.subscription_tier = "free"
            user.save(update_fields=["subscription_tier"])

            try:
                from notifications.models import Notification
                from django.urls import reverse
                Notification.create(
                    user=user,
                    notification_type="pro_expired",
                    title="Pro Subscription Expired",
                    message="Your Pro Seller subscription has expired. Renew for UGX 5,000/month to keep unlimited access.",
                    action_url=reverse("accounts:upgrade"),
                )
            except Exception:
                pass

            self.stdout.write(f"  Downgraded: {user.email}")

        self.stdout.write(self.style.SUCCESS(f"Done — {count} subscription(s) expired and downgraded."))
