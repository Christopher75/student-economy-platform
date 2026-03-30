from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Case, When, IntegerField
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from .forms import ListingForm, ListingPhotoFormSet, ListingSearchForm
from .models import Category, Listing, ListingPhoto, ListingReport, SavedListing


def marketplace_home(request):
    return redirect("marketplace:listing_list")


class ListingListView(ListView):
    model = Listing
    template_name = "marketplace/list.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        qs = Listing.objects.filter(status="available").select_related("seller", "category")
        q = self.request.GET.get("q", "").strip()
        category_slug = self.request.GET.get("category", "")
        condition = self.request.GET.get("condition", "")
        min_price = self.request.GET.get("min_price", "")
        max_price = self.request.GET.get("max_price", "")
        university = self.request.GET.get("university", "")
        sort = self.request.GET.get("sort", "-created_at")

        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if condition:
            qs = qs.filter(condition=condition)
        if min_price:
            try:
                qs = qs.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                qs = qs.filter(price__lte=float(max_price))
            except ValueError:
                pass
        if university:
            qs = qs.filter(university__icontains=university)

        allowed_sorts = {"price", "-price", "-created_at", "-views_count"}
        # Pro sellers get priority placement
        qs = qs.annotate(
            is_pro_seller=Case(
                When(seller__subscription_tier='pro', then=1),
                default=0,
                output_field=IntegerField(),
            )
        )
        return qs.order_by("-is_featured", "-is_pro_seller", sort if sort in allowed_sorts else "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.all()
        ctx["condition_choices"] = Listing.CONDITION_CHOICES
        ctx["total_listings"] = self.get_queryset().count()
        return ctx


class ListingDetailView(DetailView):
    model = Listing
    template_name = "marketplace/detail.html"
    context_object_name = "listing"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment views count
        Listing.objects.filter(pk=obj.pk).update(views_count=obj.views_count + 1)
        obj.views_count += 1
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        listing = self.object
        ctx["related_listings"] = listing.get_related_listings()
        ctx["photos"] = listing.get_photos()
        ctx["primary_photo"] = listing.get_primary_photo()
        ctx["is_saved"] = False
        if self.request.user.is_authenticated:
            ctx["is_saved"] = SavedListing.objects.filter(
                user=self.request.user, listing=listing
            ).exists()
        return ctx


def _count_active_listings(user):
    """Count listings that are currently active (available or reserved, not sold/deleted)."""
    return Listing.objects.filter(seller=user).exclude(status="sold").count()


@login_required
def listing_create(request):
    user = request.user
    listing_limit = user.get_listing_limit()
    photo_limit = user.get_photo_limit()

    # Block access on GET if already at free limit
    if listing_limit is not None and _count_active_listings(user) >= listing_limit:
        if request.method == "GET":
            messages.warning(
                request,
                f"You have reached your free plan limit of {listing_limit} active listings. "
                "Upgrade to Pro to post unlimited listings."
            )
            return redirect("accounts:upgrade")

    if request.method == "POST":
        form = ListingForm(request.POST)
        if form.is_valid():
            # Re-check limit on POST (prevents race conditions and direct POST attacks)
            if listing_limit is not None and _count_active_listings(user) >= listing_limit:
                return render(request, "marketplace/create.html", {
                    "form": form,
                    "action": "Create",
                    "show_upgrade_modal": True,
                    "listing_limit": listing_limit,
                    "photo_limit": photo_limit,
                })

            listing = form.save(commit=False)
            listing.seller = user
            listing.save()

            # Respect photo limit strictly
            photo_files = request.FILES.getlist("photos")
            for i, photo_file in enumerate(photo_files[:photo_limit]):
                ListingPhoto.objects.create(
                    listing=listing,
                    image=photo_file,
                    is_primary=(i == 0),
                    order=i,
                )

            _notify_followers_new_listing(listing)
            messages.success(request, "Your listing has been created successfully!")
            return redirect(listing.get_absolute_url())
    else:
        form = ListingForm(initial={"university": getattr(user, "university", "")})

    return render(
        request,
        "marketplace/create.html",
        {
            "form": form,
            "action": "Create",
            "listing_limit": listing_limit,
            "photo_limit": photo_limit,
        },
    )


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller != request.user:
        return HttpResponseForbidden("You are not allowed to edit this listing.")

    photo_limit = request.user.get_photo_limit()

    if request.method == "POST":
        form = ListingForm(request.POST, instance=listing)
        if form.is_valid():
            form.save()

            # Add new photos — never exceed this user's photo limit
            photo_files = request.FILES.getlist("photos")
            existing_count = listing.photos.count()
            slots_remaining = max(0, photo_limit - existing_count)
            for i, photo_file in enumerate(photo_files[:slots_remaining]):
                ListingPhoto.objects.create(
                    listing=listing,
                    image=photo_file,
                    is_primary=(existing_count == 0 and i == 0),
                    order=existing_count + i,
                )

            messages.success(request, "Listing updated successfully.")
            return redirect(listing.get_absolute_url())
    else:
        form = ListingForm(instance=listing)

    return render(
        request,
        "marketplace/create.html",
        {
            "form": form,
            "listing": listing,
            "action": "Edit",
            "photo_limit": photo_limit,
        },
    )


@login_required
def delete_listing_photo(request, pk):
    """Remove a single photo from a listing."""
    photo = get_object_or_404(ListingPhoto, pk=pk)
    if photo.listing.seller != request.user:
        return HttpResponseForbidden("You cannot delete this photo.")
    if request.method != "POST":
        return HttpResponseForbidden()
    listing_pk = photo.listing.pk
    photo.delete()
    messages.success(request, "Photo removed.")
    return redirect("marketplace:listing_edit", pk=listing_pk)


@login_required
def my_listings(request):
    """Show all listings by the current user, regardless of status."""
    listings = Listing.objects.filter(seller=request.user).prefetch_related("photos").order_by("-created_at")
    return render(request, "marketplace/my_listings.html", {"listings": listings})


@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller != request.user:
        return HttpResponseForbidden("You are not allowed to delete this listing.")

    if request.method == "POST":
        listing.delete()
        messages.success(request, "Listing deleted successfully.")
        next_url = request.POST.get("next") or request.GET.get("next")
        return redirect(next_url or "marketplace:my_listings")

    return render(request, "marketplace/confirm_delete.html", {"listing": listing})


@login_required
def mark_sold(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller != request.user:
        return HttpResponseForbidden("Only the seller can mark a listing as sold.")

    listing.status = "sold"
    listing.save()

    # Notify users who saved this listing
    _notify_saved_users_sold(listing)

    messages.success(request, f'"{listing.title}" has been marked as sold.')
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("marketplace:my_listings")


@login_required
def relist(request, pk):
    """Put a sold/reserved listing back to available."""
    if request.method != "POST":
        return HttpResponseForbidden()
    listing = get_object_or_404(Listing, pk=pk)
    if listing.seller != request.user:
        return HttpResponseForbidden("Only the seller can relist.")
    listing.status = "available"
    listing.save(update_fields=["status"])
    messages.success(request, f'"{listing.title}" is now listed as available again.')
    return redirect("marketplace:my_listings")


@login_required
def toggle_save(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()

    listing = get_object_or_404(Listing, pk=pk)
    saved, created = SavedListing.objects.get_or_create(user=request.user, listing=listing)

    if not created:
        saved.delete()
        is_saved = False
        msg = "Listing removed from your wishlist."
    else:
        is_saved = True
        msg = "Listing saved to your wishlist."

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"saved": is_saved, "message": msg})

    messages.success(request, msg)
    return redirect(listing.get_absolute_url())


class WishlistView(LoginRequiredMixin, ListView):
    model = SavedListing
    template_name = "marketplace/wishlist.html"
    context_object_name = "saved_listings"
    paginate_by = 12

    def get_queryset(self):
        return SavedListing.objects.filter(user=self.request.user).select_related(
            "listing", "listing__seller", "listing__category"
        )


@login_required
def report_listing(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if request.method == "POST":
        reason = request.POST.get("reason")
        description = request.POST.get("description", "")

        valid_reasons = [r[0] for r in ListingReport.REASON_CHOICES]
        if reason not in valid_reasons:
            messages.error(request, "Please select a valid reason for your report.")
            return redirect(listing.get_absolute_url())

        # Prevent duplicate reports
        already_reported = ListingReport.objects.filter(
            reporter=request.user, listing=listing, is_resolved=False
        ).exists()
        if already_reported:
            messages.warning(request, "You have already reported this listing.")
            return redirect(listing.get_absolute_url())

        ListingReport.objects.create(
            reporter=request.user,
            listing=listing,
            reason=reason,
            description=description,
        )
        messages.success(request, "Thank you for your report. Our team will review it.")

    return redirect(listing.get_absolute_url())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _notify_followers_new_listing(listing):
    """Create in-app notifications for followers of the seller when a new listing is posted."""
    try:
        from notifications.models import Notification
        seller = listing.seller
        # If accounts has a followers concept, notify them; otherwise skip gracefully
        followers = getattr(seller, "followers", None)
        if followers is None:
            return
        for follow_obj in followers.all():
            follower = getattr(follow_obj, "follower", follow_obj)
            Notification.objects.create(
                recipient=follower,
                actor=seller,
                verb="posted a new listing",
                target_content_type=None,
                target_object_id=listing.pk,
                message=f'{seller.display_name} posted a new listing: {listing.title}',
            )
    except Exception:
        pass


def _notify_saved_users_sold(listing):
    """Notify users who saved a listing when it is marked as sold."""
    try:
        from notifications.models import Notification
        from django.urls import reverse
        for saved in SavedListing.objects.filter(listing=listing).select_related("user"):
            Notification.objects.create(
                user=saved.user,
                notification_type="item_sold",
                title=f'"{listing.title}" has been sold',
                message=f'A listing you saved — "{listing.title}" — has been marked as sold.',
                action_url=reverse("marketplace:listing_detail", kwargs={"pk": listing.pk}),
            )
    except Exception:
        pass
