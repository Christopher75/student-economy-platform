from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations",
    )
    listing = models.ForeignKey(
        "marketplace.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    booking = models.ForeignKey(
        "skills.SkillBooking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_message_at"]

    def __str__(self):
        participant_names = ", ".join(
            str(u) for u in self.participants.all()
        )
        return f"Conversation between {participant_names}"

    def get_other_participant(self, user):
        """Return the other participant in the conversation (for 2-person chats)."""
        return self.participants.exclude(pk=user.pk).first()

    def get_unread_count(self, user):
        """Return count of messages the given user has not yet read."""
        return self.messages.filter(
            read_at__isnull=True
        ).exclude(sender=user).count()

    @property
    def last_message(self):
        return self.messages.order_by("-created_at").first()

    @property
    def subject(self):
        if self.listing_id:
            return self.listing.title
        if self.booking_id:
            return self.booking.skill.title
        return "Direct Message"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender} at {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def is_read(self):
        return self.read_at is not None
