from django.contrib import admin

from .models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "content", "created_at", "read_at")
    can_delete = False
    show_change_link = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "participant_list", "last_message_at", "created_at")
    list_filter = ("created_at", "last_message_at")
    search_fields = ("participants__username", "listing__title", "booking__skill__title")
    readonly_fields = ("created_at", "last_message_at")
    filter_horizontal = ("participants",)
    inlines = [MessageInline]

    def subject(self, obj):
        return obj.subject
    subject.short_description = "Subject"

    def participant_list(self, obj):
        return ", ".join(str(u) for u in obj.participants.all())
    participant_list.short_description = "Participants"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "sender", "conversation", "short_content", "created_at", "is_read")
    list_filter = ("created_at", "read_at")
    search_fields = ("sender__username", "content")
    readonly_fields = ("created_at",)

    def short_content(self, obj):
        return obj.content[:80] + ("…" if len(obj.content) > 80 else "")
    short_content.short_description = "Content"

    def is_read(self, obj):
        return obj.is_read
    is_read.boolean = True
    is_read.short_description = "Read"
