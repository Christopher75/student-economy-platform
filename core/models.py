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
        return f"[{self.get_category_display()}] {self.subject} — {self.email}"
