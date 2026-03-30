from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class SupportTicket(models.Model):
    CATEGORY_CHOICES = [
        ('payment', 'Payment Issue'),
        ('account', 'Account Problem'),
        ('listing', 'Listing / Skill Issue'),
        ('bug', 'Report a Bug'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    name = models.CharField(max_length=150)
    email = models.EmailField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        return f"[{self.get_category_display()}] #{self.pk} — {self.subject}"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('ticket_detail', kwargs={'pk': self.pk})

    @property
    def has_unread_admin_reply(self):
        return self.replies.filter(is_admin_reply=True, read_by_user=False).exists()


class SupportReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    is_admin_reply = models.BooleanField(default=False)
    read_by_user = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Reply'
        verbose_name_plural = 'Replies'

    def __str__(self):
        who = 'Admin' if self.is_admin_reply else (self.sent_by.display_name if self.sent_by else 'User')
        return f"Reply by {who} on #{self.ticket.pk}"
