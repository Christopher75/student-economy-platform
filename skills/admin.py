from django.contrib import admin
from django.utils.html import format_html

from .models import Review, SkillBooking, SkillCategory, SkillOffering, SkillPortfolioItem


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]


class SkillPortfolioItemInline(admin.TabularInline):
    model = SkillPortfolioItem
    extra = 1
    fields = ["title", "description", "image", "link", "order"]


@admin.register(SkillOffering)
class SkillOfferingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "provider",
        "category",
        "delivery_method",
        "price_type",
        "price_min",
        "price_max",
        "status",
        "is_featured",
        "views_count",
        "average_rating_display",
        "created_at",
    ]
    list_filter = ["status", "delivery_method", "price_type", "is_featured", "category", "university"]
    search_fields = ["title", "description", "provider__email", "provider__full_name", "university"]
    list_editable = ["is_featured", "status"]
    readonly_fields = ["views_count", "created_at", "updated_at"]
    inlines = [SkillPortfolioItemInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    actions = ["mark_featured", "unmark_featured", "activate_offerings", "pause_offerings"]

    def average_rating_display(self, obj):
        return f"{obj.average_rating} ({obj.total_reviews})"
    average_rating_display.short_description = "Rating (reviews)"

    @admin.action(description="Mark selected offerings as featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove featured status from selected offerings")
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="Activate selected offerings")
    def activate_offerings(self, request, queryset):
        queryset.update(status="active")

    @admin.action(description="Pause selected offerings")
    def pause_offerings(self, request, queryset):
        queryset.update(status="paused")


@admin.register(SkillPortfolioItem)
class SkillPortfolioItemAdmin(admin.ModelAdmin):
    list_display = ["title", "skill", "order", "thumbnail"]
    search_fields = ["title", "skill__title"]
    list_filter = ["skill__category"]

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px;" />', obj.image.url)
        return "-"
    thumbnail.short_description = "Preview"


@admin.register(SkillBooking)
class SkillBookingAdmin(admin.ModelAdmin):
    list_display = [
        "skill",
        "client",
        "provider",
        "status",
        "requested_date",
        "price_agreed",
        "created_at",
    ]
    list_filter = ["status", "requested_date", "created_at"]
    search_fields = [
        "skill__title",
        "client__email",
        "client__full_name",
        "provider__email",
        "provider__full_name",
    ]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    actions = ["mark_confirmed", "mark_completed", "mark_cancelled"]

    @admin.action(description="Mark selected bookings as confirmed")
    def mark_confirmed(self, request, queryset):
        queryset.filter(status="pending").update(status="confirmed")

    @admin.action(description="Mark selected bookings as completed")
    def mark_completed(self, request, queryset):
        queryset.filter(status="confirmed").update(status="completed")

    @admin.action(description="Mark selected bookings as cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.exclude(status="completed").update(status="cancelled")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "skill",
        "reviewer",
        "reviewee",
        "rating",
        "review_type",
        "created_at",
    ]
    list_filter = ["rating", "review_type", "created_at"]
    search_fields = [
        "skill__title",
        "reviewer__email",
        "reviewee__email",
        "comment",
    ]
    readonly_fields = ["booking", "reviewer", "reviewee", "skill", "review_type", "created_at"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
