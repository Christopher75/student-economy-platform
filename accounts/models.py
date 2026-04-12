import hashlib
import random
import string
import uuid
from datetime import date

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone


def _generate_otp():
    """Return a random 6-digit numeric OTP string."""
    return ''.join(random.choices(string.digits, k=6))


def _hash_otp(otp):
    """Return SHA-256 hex digest of the OTP. Never store the plain value."""
    return hashlib.sha256(otp.encode()).hexdigest()


class CustomUser(AbstractUser):
    YEAR_CHOICES = [(i, f'Year {i}') for i in range(1, 7)]
    VERIFICATION_STATUS = [
        ('unverified', 'Not Verified'),
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    SUBSCRIPTION_TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro Seller'),
    ]
    PRO_ACTIVATED_BY_CHOICES = [
        ('manual', 'Manual MoMo'),
        ('admin', 'Admin Grant'),
        ('simulated', 'Demo'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    student_id = models.CharField(max_length=50, unique=True, db_index=True)
    university = models.CharField(max_length=150)
    course = models.CharField(max_length=150)
    year_of_study = models.IntegerField(choices=YEAR_CHOICES, default=1)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default='unverified'
    )
    # Document verification
    id_card_photo = models.ImageField(
        upload_to='verification/id_cards/', null=True, blank=True
    )
    selfie_photo = models.ImageField(
        upload_to='verification/selfies/', null=True, blank=True
    )
    verification_submitted_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_at = models.DateTimeField(null=True, blank=True)
    verification_reviewed_by = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_verifications',
    )
    verification_rejection_reason = models.TextField(blank=True)
    # Registration metadata
    registration_ip = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    reputation_score = models.FloatField(default=0.0)

    # Subscription
    subscription_tier = models.CharField(max_length=20, choices=SUBSCRIPTION_TIER_CHOICES, default='free')
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    pro_activated_by = models.CharField(max_length=20, choices=PRO_ACTIVATED_BY_CHOICES, null=True, blank=True)

    # Analytics counters
    profile_view_count = models.IntegerField(default=0)
    daily_messages_sent = models.IntegerField(default=0)
    daily_messages_reset_date = models.DateField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name', 'student_id', 'university', 'course', 'phone_number']

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        permissions = [
            ('can_manage_payments', 'Can manage subscription payments'),
            ('can_review_verifications', 'Can review identity verifications'),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.username})

    @property
    def display_name(self):
        return self.full_name or self.username

    @property
    def activity_status(self):
        from django.utils import timezone
        if not self.last_seen:
            return 'inactive'
        delta = timezone.now() - self.last_seen
        if delta.days == 0:
            return 'today'
        elif delta.days <= 7:
            return 'this_week'
        return 'inactive'

    def is_pro(self):
        """Returns True if user has an active Pro subscription. Auto-downgrades if expired."""
        if self.subscription_tier == 'pro':
            if self.subscription_end and self.subscription_end >= date.today():
                return True
            else:
                # Subscription expired — downgrade automatically
                self.subscription_tier = 'free'
                self.save(update_fields=['subscription_tier'])
                return False
        return False

    def can_send_message(self):
        """Check whether user is allowed to send a message today."""
        if self.is_pro():
            return True
        today = date.today()
        # Reset counter if it's a new day
        if self.daily_messages_reset_date != today:
            self.daily_messages_sent = 0
            self.daily_messages_reset_date = today
            self.save(update_fields=['daily_messages_sent', 'daily_messages_reset_date'])
        return self.daily_messages_sent < 15

    def record_message_sent(self):
        """Increment the daily message counter."""
        today = date.today()
        if self.daily_messages_reset_date != today:
            self.daily_messages_sent = 0
            self.daily_messages_reset_date = today
        self.daily_messages_sent += 1
        self.save(update_fields=['daily_messages_sent', 'daily_messages_reset_date'])

    def get_listing_limit(self):
        return None if self.is_pro() else 3

    def get_skill_limit(self):
        return None if self.is_pro() else 2

    def get_photo_limit(self):
        return 5 if self.is_pro() else 2

    def get_average_rating(self):
        try:
            from skills.models import Review
            reviews = Review.objects.filter(reviewee=self)
            if reviews.exists():
                total = sum(r.rating for r in reviews)
                return round(total / reviews.count(), 1)
        except Exception:
            pass
        return 0.0

    def get_review_count(self):
        try:
            from skills.models import Review
            return Review.objects.filter(reviewee=self).count()
        except Exception:
            return 0

    def get_trust_score(self):
        score = 0
        if self.is_email_verified:
            score += 15
        if self.is_verified:
            score += 20
        try:
            from marketplace.models import Listing
            marketplace_completed = Listing.objects.filter(
                seller=self, status='sold'
            ).count()
            score += min(marketplace_completed * 5, 15)
        except Exception:
            pass
        try:
            from skills.models import SkillBooking, Review
            from django.db.models import Q
            completed_bookings = SkillBooking.objects.filter(
                Q(client=self) | Q(provider=self),
                status='completed'
            ).count()
            score += min(completed_bookings * 5, 15)
            reviews = Review.objects.filter(reviewee=self)
            for r in reviews:
                if r.rating == 5:
                    score += 3
                elif r.rating == 4:
                    score += 2
                elif r.rating == 3:
                    score += 1
        except Exception:
            pass
        return max(0, min(score, 100))

    @property
    def trust_score(self):
        return self.get_trust_score()


class EmailVerificationToken(models.Model):
    """Legacy link-based email verification. Kept for backward compatibility."""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Token for {self.user.email}"

    def is_valid(self):
        return not self.is_used and (timezone.now() - self.created_at).days < 3


class EmailOTPVerification(models.Model):
    """
    6-digit OTP email verification. OTP is stored as a SHA-256 hash only.
    Created on registration, consumed when the user enters the correct code.
    """
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='email_otp'
    )
    otp_hash = models.CharField(max_length=64)
    otp_created_at = models.DateTimeField()
    otp_expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    resend_count = models.IntegerField(default=0)
    last_resent_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"OTP for {self.user.email} (verified={self.is_verified})"

    def is_expired(self):
        return timezone.now() > self.otp_expires_at

    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def remaining_attempts(self):
        return max(0, 5 - self.attempts)

    def can_resend(self):
        if self.resend_count >= 5:
            return False
        if self.last_resent_at:
            elapsed = (timezone.now() - self.last_resent_at).total_seconds()
            if elapsed < 60:
                return False
        return True

    def seconds_until_resend(self):
        if not self.last_resent_at:
            return 0
        elapsed = (timezone.now() - self.last_resent_at).total_seconds()
        remaining = 60 - elapsed
        return max(0, int(remaining))

    def refresh_otp(self):
        """Generate a new OTP, reset expiry and attempts, return the plain OTP."""
        from datetime import timedelta
        plain = _generate_otp()
        now = timezone.now()
        self.otp_hash = _hash_otp(plain)
        self.otp_created_at = now
        self.otp_expires_at = now + timedelta(minutes=15)
        self.attempts = 0
        self.locked_until = None
        self.resend_count += 1
        self.last_resent_at = now
        self.save()
        return plain

    def check_otp(self, submitted):
        """
        Validate the submitted OTP. Returns ('ok'|'expired'|'locked'|'wrong'|'max_attempts').
        Side-effects: increments attempts, may set locked_until.
        """
        if self.is_locked():
            return 'locked'
        if self.is_expired():
            return 'expired'
        if self.attempts >= 5:
            return 'max_attempts'
        if _hash_otp(submitted) == self.otp_hash:
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save(update_fields=['is_verified', 'verified_at'])
            return 'ok'
        self.attempts += 1
        if self.attempts >= 5:
            from datetime import timedelta
            self.locked_until = timezone.now() + timedelta(minutes=30)
        self.save(update_fields=['attempts', 'locked_until'])
        return 'wrong'


def _generate_reference_code():
    chars = string.ascii_uppercase + string.digits
    for _ in range(100):
        suffix = ''.join(random.choices(chars, k=4))
        code = f'SEP-PRO-{suffix}'
        if not SubscriptionPayment.objects.filter(reference_code=code).exists():
            return code
    raise ValueError("Could not generate a unique reference code")


class SubscriptionPayment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subscription_payments')
    reference_code = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=0, default=5000)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    momo_transaction_id = models.CharField(max_length=100, blank=True)
    phone_number_used = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        CustomUser,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='confirmed_payments',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.reference_code} — {self.user.display_name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.reference_code:
            self.reference_code = _generate_reference_code()
        super().save(*args, **kwargs)
