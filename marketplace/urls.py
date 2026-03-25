from django.urls import path

from . import views

app_name = "marketplace"

urlpatterns = [
    # Home / redirect
    path("", views.marketplace_home, name="marketplace_home"),

    # Listings
    path("listings/", views.ListingListView.as_view(), name="listing_list"),
    path("listings/mine/", views.my_listings, name="my_listings"),
    path("listings/create/", views.listing_create, name="listing_create"),
    path("listings/<int:pk>/", views.ListingDetailView.as_view(), name="listing_detail"),
    path("listings/<int:pk>/edit/", views.listing_edit, name="listing_edit"),
    path("listings/<int:pk>/delete/", views.listing_delete, name="listing_delete"),
    path("listings/<int:pk>/mark-sold/", views.mark_sold, name="mark_sold"),
    path("listings/<int:pk>/relist/", views.relist, name="relist"),
    path("listings/<int:pk>/save/", views.toggle_save, name="toggle_save"),
    path("photos/<int:pk>/delete/", views.delete_listing_photo, name="delete_listing_photo"),
    path("listings/<int:pk>/report/", views.report_listing, name="report_listing"),

    # Wishlist
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
]
