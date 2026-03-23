from django.db import models
from django.conf import settings
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=100, blank=True, help_text="Emoji or icon CSS class")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Sort order (lower = first)")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("marketplace:listing_list") + f"?category={self.slug}"


class Listing(models.Model):
    CONDITION_CHOICES = [
        ("new", "New"),
        ("like_new", "Like New"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("poor", "Poor"),
    ]
    STATUS_CHOICES = [
        ("available", "Available"),
        ("sold", "Sold"),
        ("reserved", "Reserved"),
    ]

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listings",
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    price = models.DecimalField(max_digits=10, decimal_places=0)
    negotiable = models.BooleanField(default=False)
    university = models.CharField(max_length=150, blank=True)
    campus_location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="available")
    views_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("marketplace:listing_detail", kwargs={"pk": self.pk})

    def get_primary_photo(self):
        primary = self.photos.filter(is_primary=True).first()
        if primary:
            return primary
        return self.photos.order_by("order").first()

    def get_photos(self):
        return self.photos.order_by("order")

    def get_related_listings(self):
        qs = Listing.objects.filter(
            category=self.category,
            status="available",
        ).exclude(seller=self.seller).exclude(pk=self.pk)
        return qs[:6]


class ListingPhoto(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="listings/")
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Photo for {self.listing.title}"


class SavedListing(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_listings",
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="saved_by")
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "listing")
        ordering = ["-saved_at"]

    def __str__(self):
        return f"{self.user} saved {self.listing.title}"


class ListingReport(models.Model):
    REASON_CHOICES = [
        ("inappropriate", "Inappropriate Content"),
        ("spam", "Spam"),
        ("fake", "Fake Listing"),
        ("misleading", "Misleading Information"),
        ("other", "Other"),
    ]

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_made",
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report by {self.reporter} on {self.listing.title}"
