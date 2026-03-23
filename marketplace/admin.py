from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Listing, ListingPhoto, ListingReport, SavedListing


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "icon", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "description"]


class ListingPhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 1
    fields = ["image", "is_primary", "order"]
    readonly_fields = []


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "seller",
        "category",
        "price",
        "condition",
        "status",
        "is_featured",
        "views_count",
        "created_at",
    ]
    list_filter = ["status", "condition", "is_featured", "category", "university"]
    search_fields = ["title", "description", "seller__email", "seller__full_name", "university"]
    list_editable = ["is_featured", "status"]
    readonly_fields = ["views_count", "created_at", "updated_at"]
    inlines = [ListingPhotoInline]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    actions = ["mark_featured", "unmark_featured", "mark_available", "mark_sold"]

    @admin.action(description="Mark selected listings as featured")
    def mark_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove featured status from selected listings")
    def unmark_featured(self, request, queryset):
        queryset.update(is_featured=False)

    @admin.action(description="Mark selected listings as available")
    def mark_available(self, request, queryset):
        queryset.update(status="available")

    @admin.action(description="Mark selected listings as sold")
    def mark_sold(self, request, queryset):
        queryset.update(status="sold")


@admin.register(ListingPhoto)
class ListingPhotoAdmin(admin.ModelAdmin):
    list_display = ["listing", "is_primary", "order", "thumbnail"]
    list_filter = ["is_primary"]
    search_fields = ["listing__title"]

    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px;" />', obj.image.url)
        return "-"
    thumbnail.short_description = "Preview"


@admin.register(SavedListing)
class SavedListingAdmin(admin.ModelAdmin):
    list_display = ["user", "listing", "saved_at"]
    list_filter = ["saved_at"]
    search_fields = ["user__email", "listing__title"]
    date_hierarchy = "saved_at"


@admin.register(ListingReport)
class ListingReportAdmin(admin.ModelAdmin):
    list_display = ["reporter", "listing", "reason", "is_resolved", "created_at"]
    list_filter = ["reason", "is_resolved", "created_at"]
    search_fields = ["reporter__email", "listing__title", "description"]
    list_editable = ["is_resolved"]
    readonly_fields = ["reporter", "listing", "reason", "description", "created_at"]
    date_hierarchy = "created_at"

    actions = ["resolve_reports"]

    @admin.action(description="Mark selected reports as resolved")
    def resolve_reports(self, request, queryset):
        queryset.update(is_resolved=True)
