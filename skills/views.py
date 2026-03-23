from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import DetailView, ListView

from .forms import BookingRequestForm, ReviewForm, SkillOfferingForm
from .models import Review, SkillBooking, SkillCategory, SkillOffering, SkillPortfolioItem


# ---------------------------------------------------------------------------
# Skill Offerings
# ---------------------------------------------------------------------------

class SkillListView(ListView):
    model = SkillOffering
    template_name = "skills/list.html"
    context_object_name = "skills"
    paginate_by = 12

    def get_queryset(self):
        qs = SkillOffering.objects.filter(status="active").select_related("provider", "category")

        category_slug = self.request.GET.get("category")
        delivery = self.request.GET.get("delivery_method")
        min_price = self.request.GET.get("min_price")
        max_price = self.request.GET.get("max_price")
        university = self.request.GET.get("university")
        query = self.request.GET.get("q")

        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if delivery:
            qs = qs.filter(delivery_method=delivery)
        if min_price:
            try:
                qs = qs.filter(price_min__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                qs = qs.filter(price_max__lte=float(max_price))
            except ValueError:
                pass
        if university:
            qs = qs.filter(university__icontains=university)

        return qs.order_by("-is_featured", "-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = SkillCategory.objects.all()
        ctx["delivery_choices"] = SkillOffering.DELIVERY_CHOICES
        ctx["selected_category"] = self.request.GET.get("category", "")
        ctx["selected_delivery"] = self.request.GET.get("delivery_method", "")
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class SkillDetailView(DetailView):
    model = SkillOffering
    template_name = "skills/detail.html"
    context_object_name = "skill"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        SkillOffering.objects.filter(pk=obj.pk).update(views_count=obj.views_count + 1)
        obj.views_count += 1
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        skill = self.object
        ctx["portfolio_items"] = skill.portfolio_items.all()
        ctx["reviews"] = Review.objects.filter(
            skill=skill, review_type="client_to_provider"
        ).select_related("reviewer")
        ctx["average_rating"] = skill.average_rating
        ctx["total_reviews"] = skill.total_reviews
        ctx["can_book"] = (
            self.request.user.is_authenticated
            and self.request.user != skill.provider
            and skill.status == "active"
        )
        return ctx


@login_required
def skill_create(request):
    if request.method == "POST":
        form = SkillOfferingForm(request.POST)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.provider = request.user
            skill.save()

            # Handle simple portfolio image uploads
            portfolio_files = request.FILES.getlist("portfolio_images")
            for i, img_file in enumerate(portfolio_files[:5]):
                SkillPortfolioItem.objects.create(
                    skill=skill,
                    title=img_file.name.rsplit(".", 1)[0][:200],
                    image=img_file,
                    order=i,
                )

            messages.success(request, "Your skill offering has been published!")
            return redirect(skill.get_absolute_url())
    else:
        form = SkillOfferingForm(initial={"university": getattr(request.user, "university", "")})

    return render(
        request,
        "skills/create.html",
        {"form": form, "action": "Create"},
    )


@login_required
def skill_edit(request, pk):
    skill = get_object_or_404(SkillOffering, pk=pk)
    if skill.provider != request.user:
        return HttpResponseForbidden("You are not allowed to edit this skill offering.")

    if request.method == "POST":
        form = SkillOfferingForm(request.POST, instance=skill)
        if form.is_valid():
            form.save()

            # Add any new portfolio images uploaded
            portfolio_files = request.FILES.getlist("portfolio_images")
            existing_count = skill.portfolio_items.count()
            for i, img_file in enumerate(portfolio_files[:max(0, 5 - existing_count)]):
                SkillPortfolioItem.objects.create(
                    skill=skill,
                    title=img_file.name.rsplit(".", 1)[0][:200],
                    image=img_file,
                    order=existing_count + i,
                )

            messages.success(request, "Skill offering updated successfully.")
            return redirect(skill.get_absolute_url())
    else:
        form = SkillOfferingForm(instance=skill)

    return render(
        request,
        "skills/create.html",
        {"form": form, "skill": skill, "action": "Edit"},
    )


@login_required
def skill_delete(request, pk):
    skill = get_object_or_404(SkillOffering, pk=pk)
    if skill.provider != request.user:
        return HttpResponseForbidden("You are not allowed to delete this skill offering.")

    if request.method == "POST":
        skill.delete()
        messages.success(request, "Skill offering deleted successfully.")
        return redirect("skills:skill_list")

    return render(request, "skills/confirm_delete.html", {"skill": skill})


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------

@login_required
def booking_request(request, skill_pk):
    skill = get_object_or_404(SkillOffering, pk=skill_pk, status="active")

    if skill.provider == request.user:
        messages.error(request, "You cannot book your own skill offering.")
        return redirect(skill.get_absolute_url())

    if request.method == "POST":
        form = BookingRequestForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.skill = skill
            booking.client = request.user
            booking.provider = skill.provider
            booking.save()

            _notify_provider_new_booking(booking)

            messages.success(
                request,
                f"Booking request sent to {skill.provider.display_name}. "
                "You will be notified when they respond.",
            )
            return redirect("bookings:booking_detail", pk=booking.pk)
    else:
        form = BookingRequestForm()

    return render(
        request,
        "skills/booking_request.html",
        {"form": form, "skill": skill},
    )


class MyBookingsView(LoginRequiredMixin, ListView):
    model = SkillBooking
    template_name = "bookings/list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return SkillBooking.objects.filter(
            Q(client=self.request.user) | Q(provider=self.request.user)
        ).select_related("skill", "client", "provider").order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["client_bookings"] = SkillBooking.objects.filter(client=user).select_related(
            "skill", "provider"
        ).order_by("-created_at")
        ctx["provider_bookings"] = SkillBooking.objects.filter(provider=user).select_related(
            "skill", "client"
        ).order_by("-created_at")
        return ctx


class BookingDetailView(LoginRequiredMixin, DetailView):
    model = SkillBooking
    template_name = "bookings/detail.html"
    context_object_name = "booking"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if obj.client != user and obj.provider != user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        booking = self.object
        user = self.request.user
        ctx["is_provider"] = booking.provider == user
        ctx["is_client"] = booking.client == user
        ctx["has_reviewed"] = Review.objects.filter(booking=booking, reviewer=user).exists()
        return ctx


@login_required
def accept_booking(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    booking = get_object_or_404(SkillBooking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Only the provider can accept bookings.")
    if booking.status != "pending":
        messages.error(request, "This booking cannot be accepted in its current state.")
        return redirect("bookings:booking_detail", pk=pk)

    booking.status = "confirmed"
    booking.save()
    _notify_client_booking_update(booking, "accepted")
    messages.success(request, "Booking accepted. The client has been notified.")
    return redirect("bookings:booking_detail", pk=pk)


@login_required
def decline_booking(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    booking = get_object_or_404(SkillBooking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Only the provider can decline bookings.")
    if booking.status not in ("pending", "confirmed"):
        messages.error(request, "This booking cannot be declined in its current state.")
        return redirect("bookings:booking_detail", pk=pk)

    booking.status = "cancelled"
    booking.save()
    _notify_client_booking_update(booking, "declined")
    messages.success(request, "Booking declined. The client has been notified.")
    return redirect("bookings:my_bookings")


@login_required
def complete_booking(request, pk):
    if request.method != "POST":
        return HttpResponseForbidden()
    booking = get_object_or_404(SkillBooking, pk=pk)
    if booking.provider != request.user:
        return HttpResponseForbidden("Only the provider can mark bookings as completed.")
    if booking.status != "confirmed":
        messages.error(request, "Only confirmed bookings can be marked as completed.")
        return redirect("bookings:booking_detail", pk=pk)

    booking.status = "completed"
    booking.save()
    _notify_client_booking_update(booking, "completed")
    messages.success(
        request,
        "Booking marked as completed. "
        "Both parties can now leave a review.",
    )
    return redirect("bookings:booking_detail", pk=pk)


@login_required
def leave_review(request, pk):
    booking = get_object_or_404(SkillBooking, pk=pk)
    user = request.user

    # Only participants of a completed booking can leave reviews
    if user not in (booking.client, booking.provider):
        return HttpResponseForbidden("You are not a participant in this booking.")
    if not booking.can_review:
        messages.error(request, "You can only leave a review for completed bookings.")
        return redirect("bookings:booking_detail", pk=pk)

    already_reviewed = Review.objects.filter(booking=booking, reviewer=user).exists()
    if already_reviewed:
        messages.info(request, "You have already left a review for this booking.")
        return redirect("bookings:booking_detail", pk=pk)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.reviewer = user

            if user == booking.client:
                review.reviewee = booking.provider
                review.review_type = "client_to_provider"
            else:
                review.reviewee = booking.client
                review.review_type = "provider_to_client"

            review.skill = booking.skill
            review.save()

            messages.success(request, "Your review has been submitted. Thank you!")
            return redirect("bookings:booking_detail", pk=pk)
    else:
        form = ReviewForm()

    return render(
        request,
        "skills/leave_review.html",
        {"form": form, "booking": booking},
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _notify_provider_new_booking(booking):
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=booking.provider,
            actor=booking.client,
            verb="sent a booking request",
            target_object_id=booking.pk,
            message=(
                f"{booking.client.display_name} requested a booking for "
                f'"{booking.skill.title}".'
            ),
        )
    except Exception:
        pass


def _notify_client_booking_update(booking, action):
    try:
        from notifications.models import Notification
        verb_map = {
            "accepted": "accepted your booking request",
            "declined": "declined your booking request",
            "completed": "marked your booking as completed",
        }
        verb = verb_map.get(action, action)
        Notification.objects.create(
            recipient=booking.client,
            actor=booking.provider,
            verb=verb,
            target_object_id=booking.pk,
            message=(
                f"{booking.provider.display_name} {verb} for "
                f'"{booking.skill.title}".'
            ),
        )
    except Exception:
        pass
