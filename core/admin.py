from django.contrib import admin
from .models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'category', 'status', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-created_at',)
    list_per_page = 25
    readonly_fields = ('user', 'name', 'email', 'category', 'subject', 'message', 'created_at')
    fieldsets = (
        ('Ticket Info', {'fields': ('user', 'name', 'email', 'category', 'subject', 'message', 'created_at')}),
        ('Admin', {'fields': ('status', 'admin_notes')}),
    )

    @admin.action(description='Mark selected tickets as resolved')
    def mark_resolved(self, request, queryset):
        queryset.update(status='resolved')

    actions = ['mark_resolved']
