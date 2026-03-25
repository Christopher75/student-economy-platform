import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class CustomUser(AbstractUser):
    YEAR_CHOICES = [(i, f'Year {i}') for i in range(1, 7)]
    VERIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    student_id = models.CharField(max_length=50, unique=True)
    university = models.CharField(max_length=150)
    course = models.CharField(max_length=150)
    year_of_study = models.IntegerField(choices=YEAR_CHOICES, default=1)
    phone_number = models.CharField(max_length=20)
    profile_photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default='pending')
    last_seen = models.DateTimeField(null=True, blank=True)
    reputation_score = models.FloatField(default=0.0)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name', 'student_id', 'university', 'course', 'phone_number']

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

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
            score += 20
        if self.is_verified:
            score += 30
        try:
            from skills.models import SkillBooking, Review
            from django.db.models import Q
            completed = SkillBooking.objects.filter(
                Q(client=self) | Q(provider=self),
                status='completed'
            ).count()
            score += min(completed * 10, 30)
            # Up to 20 points for positive reviews (avg rating ≥ 4)
            avg = self.get_average_rating()
            if avg >= 4.5:
                score += 20
            elif avg >= 4.0:
                score += 15
            elif avg >= 3.0:
                score += 5
        except Exception:
            pass
        return min(score, 100)

    @property
    def trust_score(self):
        return self.get_trust_score()


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Token for {self.user.email}"

    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and (timezone.now() - self.created_at).days < 3
