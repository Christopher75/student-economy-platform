from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class SkillCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=100, blank=True, help_text="Emoji or icon CSS class")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Sort order (lower = first)")

    class Meta:
        verbose_name = "Skill Category"
        verbose_name_plural = "Skill Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("skills:skill_list") + f"?category={self.slug}"


class SkillOffering(models.Model):
    DELIVERY_CHOICES = [
        ("in_person", "In Person"),
        ("online", "Online"),
        ("both", "In Person & Online"),
    ]
    PRICE_TYPE_CHOICES = [
        ("fixed", "Fixed Price"),
        ("hourly", "Hourly Rate"),
        ("negotiable", "Negotiable"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("paused", "Paused"),
        ("inactive", "Inactive"),
    ]

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="skill_offerings",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        SkillCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offerings",
    )
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default="both")
    price_type = models.CharField(max_length=20, choices=PRICE_TYPE_CHOICES, default="negotiable")
    price_min = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    price_max = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    estimated_duration = models.CharField(
        max_length=100, blank=True, help_text='e.g. "1 hour", "2-3 hours"'
    )
    availability = models.TextField(
        blank=True, help_text="Describe your available days and times"
    )
    language = models.CharField(
        max_length=200, blank=True, default="English",
        help_text='e.g. "English, Luganda, Swahili"'
    )
    university = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    views_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("skills:skill_detail", kwargs={"pk": self.pk})

    @property
    def average_rating(self):
        reviews = Review.objects.filter(skill=self, review_type="client_to_provider")
        if not reviews.exists():
            return 0.0
        total = sum(r.rating for r in reviews)
        return round(total / reviews.count(), 1)

    @property
    def total_reviews(self):
        return Review.objects.filter(skill=self, review_type="client_to_provider").count()


class SkillPortfolioItem(models.Model):
    skill = models.ForeignKey(
        SkillOffering, on_delete=models.CASCADE, related_name="portfolio_items"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="portfolios/", null=True, blank=True)
    link = models.URLField(blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.title} ({self.skill.title})"


class SkillBooking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    skill = models.ForeignKey(
        SkillOffering, on_delete=models.CASCADE, related_name="bookings"
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings_as_client",
    )
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings_as_provider",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    requested_date = models.DateField()
    notes = models.TextField(blank=True)
    price_agreed = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Booking: {self.client} → {self.skill.title} ({self.status})"

    def get_absolute_url(self):
        return reverse("bookings:booking_detail", kwargs={"pk": self.pk})

    @property
    def can_review(self):
        return self.status == "completed"


class Review(models.Model):
    REVIEW_TYPE_CHOICES = [
        ("client_to_provider", "Client to Provider"),
        ("provider_to_client", "Provider to Client"),
    ]

    booking = models.ForeignKey(
        SkillBooking, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_given",
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    skill = models.ForeignKey(
        SkillOffering, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    review_type = models.CharField(max_length=25, choices=REVIEW_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("booking", "reviewer")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review by {self.reviewer} for {self.skill.title} ({self.rating}/5)"
