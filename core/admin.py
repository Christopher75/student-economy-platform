from django.contrib import admin
from django.contrib import messages as django_messages

from .models import SupportTicket, SupportReply


# ---------------------------------------------------------------------------
# Reply inline — appears inside the ticket change page
# ---------------------------------------------------------------------------

class SupportReplyInline(admin.StackedInline):
    model = SupportReply
    extra = 1          # one blank reply form at the bottom
    max_num = 20
    fields = ('message', 'is_admin_reply', 'read_by_user', 'sent_by')
    readonly_fields = ('sent_by', 'created_at')
    can_delete = False  # replies are permanent records

    def get_readonly_fields(self, request, obj=None):
        # created_at only exists on saved instances
        return ('sent_by', 'created_at') if obj else ('sent_by',)


# ---------------------------------------------------------------------------
# SupportTicket admin
# ---------------------------------------------------------------------------

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'name', 'email', 'category', 'status', 'reply_count', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-created_at',)
    list_per_page = 25
    inlines = [SupportReplyInline]
    readonly_fields = ('user', 'name', 'email', 'category', 'subject', 'message', 'created_at', 'updated_at')
    fieldsets = (
        ('Ticket Info', {
            'fields': ('user', 'name', 'email', 'category', 'subject', 'message', 'created_at', 'updated_at'),
        }),
        ('Admin', {
            'fields': ('status', 'admin_notes'),
        }),
    )

    @admin.display(description='Replies')
    def reply_count(self, obj):
        return obj.replies.count()

    @admin.action(description='Mark selected tickets as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')
        self.message_user(request, f'{queryset.count()} ticket(s) marked resolved.')

    actions = ['mark_resolved']

    def save_formset(self, request, form, formset, change):
        """
        Called after the inline formset (replies) is saved.
        For each new admin reply, auto-set sent_by = request.user and
        send an in-app notification to the ticket owner.
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, SupportReply) and not instance.pk:
                # New reply being added
                instance.sent_by = request.user
                instance.is_admin_reply = True
                instance.save()

                # Notify the ticket owner if they have a platform account
                ticket = instance.ticket
                if ticket.user:
                    _notify_ticket_reply(ticket, instance)

                self.message_user(
                    request,
                    f'Reply sent to {ticket.email} (ticket #{ticket.pk}).',
                    django_messages.SUCCESS,
                )
            else:
                instance.save()

        formset.save_m2m()


def _notify_ticket_reply(ticket, reply):
    """Send an in-app notification when admin replies to a ticket."""
    try:
        from notifications.models import Notification
        from django.urls import reverse
        Notification.create(
            user=ticket.user,
            notification_type='other',
            title=f'Support Reply: {ticket.subject}',
            message=reply.message[:200] + ('…' if len(reply.message) > 200 else ''),
            action_url=reverse('ticket_detail', kwargs={'pk': ticket.pk}),
        )
    except Exception:
        pass
