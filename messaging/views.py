from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView, DetailView

from .forms import MessageForm
from .models import Conversation, Message

User = get_user_model()


class InboxView(LoginRequiredMixin, ListView):
    """Display all conversations for the current user, most recent first."""

    template_name = "messaging/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return (
            Conversation.objects.filter(participants=self.request.user)
            .prefetch_related("participants", "messages")
            .select_related("listing", "booking__skill")
            .order_by("-last_message_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Annotate each conversation with its unread count for the current user
        conversations_with_unread = []
        for conv in context["conversations"]:
            conversations_with_unread.append({
                "conversation": conv,
                "unread_count": conv.get_unread_count(user),
                "other_participant": conv.get_other_participant(user),
                "last_message": conv.last_message,
            })
        context["conversations_with_unread"] = conversations_with_unread
        return context


class ConversationView(LoginRequiredMixin, DetailView):
    """Show all messages in a conversation and allow sending new messages."""

    template_name = "messaging/conversation.html"
    context_object_name = "conversation"

    def get_object(self, queryset=None):
        conv = get_object_or_404(Conversation, pk=self.kwargs["pk"])
        if not conv.participants.filter(pk=self.request.user.pk).exists():
            raise Http404("You are not a participant in this conversation.")
        return conv

    def get(self, request, *args, **kwargs):
        conversation = self.get_object()
        # Mark all unread messages (not sent by current user) as read
        now = timezone.now()
        conversation.messages.filter(
            read_at__isnull=True
        ).exclude(sender=request.user).update(read_at=now)

        # Also mark any message notifications pointing to this conversation as read
        try:
            from notifications.models import Notification
            from django.urls import reverse
            action_url = reverse("messaging:conversation", kwargs={"pk": conversation.pk})
            Notification.objects.filter(
                user=request.user, action_url=action_url, is_read=False
            ).update(is_read=True)
        except Exception:
            pass

        form = MessageForm()
        return render(request, self.template_name, {
            "conversation": conversation,
            "messages_list": conversation.messages.select_related("sender").all(),
            "form": form,
            "other_participant": conversation.get_other_participant(request.user),
        })

    def post(self, request, *args, **kwargs):
        conversation = self.get_object()
        user = request.user

        # Enforce daily message limit for free users
        if not user.can_send_message():
            form = MessageForm(request.POST)
            return render(request, self.template_name, {
                "conversation": conversation,
                "messages_list": conversation.messages.select_related("sender").all(),
                "form": form,
                "other_participant": conversation.get_other_participant(request.user),
                "message_limit_reached": True,
            })

        form = MessageForm(request.POST)
        if form.is_valid():
            Message.objects.create(
                conversation=conversation,
                sender=user,
                content=form.cleaned_data["content"],
            )
            # Update last_message_at on the conversation
            conversation.last_message_at = timezone.now()
            conversation.save(update_fields=["last_message_at"])

            # Record the send for daily limit tracking
            user.record_message_sent()

            # Create a notification for the other participant
            recipient = conversation.get_other_participant(user)
            if recipient:
                _create_message_notification(
                    recipient=recipient,
                    sender=user,
                    conversation=conversation,
                )

            return redirect("messaging:conversation", pk=conversation.pk)

        return render(request, self.template_name, {
            "conversation": conversation,
            "messages_list": conversation.messages.select_related("sender").all(),
            "form": form,
            "other_participant": conversation.get_other_participant(request.user),
        })


def _create_message_notification(recipient, sender, conversation):
    """Helper to create a new_message notification."""
    try:
        from notifications.models import Notification
        from django.urls import reverse
        action_url = reverse("messaging:conversation", kwargs={"pk": conversation.pk})
        Notification.create(
            user=recipient,
            notification_type="new_message",
            title="New Message",
            message=f"You have a new message from {sender.get_full_name() or sender.username}.",
            action_url=action_url,
        )
    except Exception:
        pass


@login_required
def start_conversation(request, username):
    """
    Find or create a direct conversation with the given user.
    Redirects to the conversation view.
    """
    other_user = get_object_or_404(User, username=username)

    if other_user == request.user:
        messages.error(request, "You cannot send a message to yourself.")
        return redirect("messaging:inbox")

    # Look for an existing direct conversation (no listing/booking) between these two users
    existing = (
        Conversation.objects.filter(
            participants=request.user,
            listing__isnull=True,
            booking__isnull=True,
        )
        .filter(participants=other_user)
        .first()
    )

    if existing:
        return redirect("messaging:conversation", pk=existing.pk)

    # Create a new conversation
    conversation = Conversation.objects.create()
    conversation.participants.add(request.user, other_user)
    return redirect("messaging:conversation", pk=conversation.pk)


@login_required
def start_conversation_for_skill(request, skill_pk):
    """
    Find or create a conversation about a specific skill offering.
    The provider is automatically the other participant.
    """
    from skills.models import SkillOffering

    skill = get_object_or_404(SkillOffering, pk=skill_pk)

    if skill.provider == request.user:
        messages.error(request, "You cannot message yourself about your own skill.")
        return redirect("skills:skill_detail", pk=skill.pk)

    existing = (
        Conversation.objects.filter(participants=request.user, skill=skill)
        .filter(participants=skill.provider)
        .first()
    )

    if existing:
        return redirect("messaging:conversation", pk=existing.pk)

    conversation = Conversation.objects.create(skill=skill)
    conversation.participants.add(request.user, skill.provider)
    return redirect("messaging:conversation", pk=conversation.pk)


@login_required
def start_conversation_for_listing(request, listing_pk):
    """
    Find or create a conversation about a specific marketplace listing.
    The seller is automatically the other participant.
    """
    from marketplace.models import Listing

    listing = get_object_or_404(Listing, pk=listing_pk)

    if listing.seller == request.user:
        messages.error(request, "You cannot message yourself about your own listing.")
        return redirect("marketplace:listing_detail", pk=listing.pk)

    # Look for an existing conversation about this listing between these two users
    existing = (
        Conversation.objects.filter(
            participants=request.user,
            listing=listing,
        )
        .filter(participants=listing.seller)
        .first()
    )

    if existing:
        return redirect("messaging:conversation", pk=existing.pk)

    # Create a new conversation linked to the listing
    conversation = Conversation.objects.create(listing=listing)
    conversation.participants.add(request.user, listing.seller)
    return redirect("messaging:conversation", pk=conversation.pk)
