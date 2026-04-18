from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from accounts.models import CustomUser
from marketplace.models import Listing
from chatbot.models import UserFlag
from core.models import SupportTicket


class Command(BaseCommand):
    help = 'Scans for suspicious user activity and creates flags'

    def handle(self, *args, **kwargs):
        self.stdout.write('Running suspicious activity monitor...')
        flagged = 0

        # CHECK 1: Users whose listings have 3+ reports
        reported_sellers = Listing.objects.filter(
            reports__isnull=False
        ).annotate(
            report_count=Count('reports')
        ).filter(report_count__gte=3).values_list('seller_id', flat=True)

        for uid in set(reported_sellers):
            user = CustomUser.objects.get(pk=uid)
            already = UserFlag.objects.filter(
                user=user, reason='too_many_reports', status='open'
            ).exists()
            if not already:
                UserFlag.objects.create(
                    user=user,
                    reason='too_many_reports',
                    detail=f'{user.display_name} has listings with 3 or more reports.',
                )
                self._make_admin_ticket(user, 'Too many listing reports')
                flagged += 1
                self.stdout.write(f'  Flagged: {user.display_name} — too many reports')

        # CHECK 2: Free users with more than 3 active listings
        free_over_limit = CustomUser.objects.filter(
            subscription_tier='free'
        ).annotate(
            active_count=Count('listings', filter=Q(listings__status='available'))
        ).filter(active_count__gt=3)

        for user in free_over_limit:
            already = UserFlag.objects.filter(
                user=user, reason='limit_exceeded', status='open'
            ).exists()
            if not already:
                UserFlag.objects.create(
                    user=user,
                    reason='limit_exceeded',
                    detail=f'{user.display_name} is on Free plan but has more than 3 active listings.',
                )
                flagged += 1
                self.stdout.write(f'  Flagged: {user.display_name} — exceeded free plan limit')

        # CHECK 3: Listings priced under UGX 100
        suspicious = Listing.objects.filter(
            price__lt=100, status='available'
        ).select_related('seller')

        for listing in suspicious:
            user = listing.seller
            already = UserFlag.objects.filter(
                user=user, reason='suspicious_price', status='open'
            ).exists()
            if not already:
                UserFlag.objects.create(
                    user=user,
                    reason='suspicious_price',
                    detail=f'Listing "{listing.title}" priced at only UGX {listing.price}. Possibly fake.',
                )
                flagged += 1
                self.stdout.write(f'  Flagged: {user.display_name} — suspicious price on "{listing.title}"')

        # CHECK 4: Duplicate listings (same seller, same title)
        duplicates = Listing.objects.filter(
            status='available'
        ).values('seller', 'title').annotate(
            count=Count('id')
        ).filter(count__gt=1)

        for dup in duplicates:
            user = CustomUser.objects.get(pk=dup['seller'])
            already = UserFlag.objects.filter(
                user=user, reason='duplicate_listings', status='open'
            ).exists()
            if not already:
                UserFlag.objects.create(
                    user=user,
                    reason='duplicate_listings',
                    detail=f'{user.display_name} posted {dup["count"]} identical listings titled "{dup["title"]}".',
                )
                flagged += 1
                self.stdout.write(f'  Flagged: {user.display_name} — duplicate listing "{dup["title"]}"')

        if flagged == 0:
            self.stdout.write(self.style.SUCCESS('No suspicious activity found.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Done. {flagged} new flag(s) created.'))

    def _make_admin_ticket(self, user, reason):
        SupportTicket.objects.create(
            user=user,
            name=user.display_name,
            email=user.email,
            category='other',
            subject=f'[AUTO FLAG] {reason} — {user.display_name}',
            message=(
                f'Automated monitor flagged this account.\n\n'
                f'Reason: {reason}\n'
                f'User: {user.display_name} ({user.email})\n'
                f'University: {user.university}\n\n'
                f'Please review this account in the admin panel.'
            ),
        )