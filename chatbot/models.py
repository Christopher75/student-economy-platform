from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chat_sessions'
    )
    session_key = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        user = self.user.display_name if self.user else 'Anonymous'
        return f"Chat session — {user} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class ChatMessage(models.Model):
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class UserFlag(models.Model):
    REASON_CHOICES = [
        ('too_many_reports', 'Too many listing reports'),
        ('duplicate_listings', 'Duplicate listings detected'),
        ('limit_exceeded', 'Exceeded free plan limits'),
        ('suspicious_price', 'Suspicious pricing detected'),
        ('multi_account', 'Possible multiple accounts'),
        ('message_abuse', 'Messaging limit abuse'),
        ('other', 'Other suspicious activity'),
    ]
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='flags'
    )
    reason = models.CharField(max_length=50, choices=REASON_CHOICES)
    detail = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Flag: {self.user} — {self.get_reason_display()}"