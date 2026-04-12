from datetime import date, timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages as django_messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, EmailVerificationToken, SubscriptionPayment


# ---------------------------------------------------------------------------
# Photo preview helper
# ---------------------------------------------------------------------------

def _photo_tag(field, label='Photo'):
    """Return an inline <img> tag for a Cloudinary/file ImageField, or '—'."""
    if not field:
        return '—'
    try:
        url = field.url
    except Exception:
        return '—'
    return format_html(
        '<a href="{url}" target="_blank">'
        '<img src="{url}" style="max-height:150px;max-width:220px;'
        'border-radius:6px;border:1px solid #e2e8f0;" alt="{label}">'
        '<br><small style="color:#64748b;">Click to enlarge</small></a>',
        url=url, label=label,
    )


# ---------------------------------------------------------------------------
# Helpers shared by both admin actions and save_model
# ---------------------------------------------------------------------------

def _activate_pro_for_payment(payment, confirmed_by_user):
    """Activate Pro on the payment's user and update payment record."""
    from django.urls import reverse
    payment.status = 'confirmed'
    payment.confirmed_at = timezone.now()
    payment.confirmed_by = confirmed_by_user
    payment.save(update_fields=['status', 'confirmed_at', 'confirmed_by'])

    user = payment.user
    user.subscription_tier = 'pro'
    user.subscription_start = date.today()
    user.subscription_end = date.today() + timedelta(days=30)
    user.pro_activated_by = 'manual'
    user.save(update_fields=['subscription_tier', 'subscription_start', 'subscription_end', 'pro_activated_by'])

    try:
        from notifications.models import Notification
        Notification.create(
            user=user,
            notification_type='pro_activated',
            title='Pro Subscription Activated!',
            message=(
                f'Your Pro Seller subscription is now active until '
                f'{user.subscription_end.strftime("%d %b %Y")}. '
                'Enjoy unlimited listings, skills, messages and priority placement!'
            ),
            action_url=reverse('accounts:analytics'),
        )
    except Exception:
        pass


def _reject_payment(payment, reason=''):
    """Mark payment as rejected and notify user."""
    from django.urls import reverse
    payment.status = 'rejected'
    if reason:
        payment.notes = reason
    payment.save(update_fields=['status', 'notes'])

    try:
        from notifications.models import Notification
        Notification.create(
            user=payment.user,
            notification_type='payment_rejected',
            title='Payment Not Confirmed',
            message=(
                f'Your Pro upgrade payment ({payment.reference_code}) was not confirmed.'
                + (f' Reason: {reason}' if reason else '')
                + ' Please contact support or try again.'
            ),
            action_url=reverse('accounts:upgrade'),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Custom admin actions
# ---------------------------------------------------------------------------

@admin.action(description='✅ Approve identity verification for selected users')
def approve_users(modeladmin, request, queryset):
    updated = 0
    for user in queryset.filter(verification_status='pending'):
        user.verification_status = 'verified'
        user.is_verified = True
        user.verification_reviewed_at = timezone.now()
        user.verification_reviewed_by = request.user
        user.save(update_fields=[
            'verification_status', 'is_verified',
            'verification_reviewed_at', 'verification_reviewed_by',
        ])
        updated += 1
    modeladmin.message_user(request, f'{updated} student(s) approved.', django_messages.SUCCESS)


@admin.action(description='❌ Reject identity verification for selected users')
def reject_users(modeladmin, request, queryset):
    updated = 0
    reason = 'Rejected via admin panel'
    for user in queryset.filter(verification_status='pending'):
        user.verification_status = 'rejected'
        user.is_verified = False
        user.verification_reviewed_at = timezone.now()
        user.verification_reviewed_by = request.user
        user.verification_rejection_reason = reason
        user.save(update_fields=[
            'verification_status', 'is_verified',
            'verification_reviewed_at', 'verification_reviewed_by',
            'verification_rejection_reason',
        ])
        updated += 1
    modeladmin.message_user(request, f'{updated} student(s) rejected.', django_messages.WARNING)


@admin.action(description='Confirm selected payments (activate Pro for 30 days)')
def confirm_payments(modeladmin, request, queryset):
    confirmed = 0
    for payment in queryset.filter(status='pending'):
        _activate_pro_for_payment(payment, request.user)
        confirmed += 1
    modeladmin.message_user(request, f'{confirmed} payment(s) confirmed and Pro activated.', django_messages.SUCCESS)


@admin.action(description='Reject selected payments')
def reject_payments(modeladmin, request, queryset):
    rejected = 0
    for payment in queryset.filter(status='pending'):
        _reject_payment(payment)
        rejected += 1
    modeladmin.message_user(request, f'{rejected} payment(s) rejected.', django_messages.WARNING)


# ---------------------------------------------------------------------------
# CustomUser admin
# ---------------------------------------------------------------------------

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'full_name', 'university',
        'verification_status', 'is_verified', 'is_email_verified',
        'subscription_tier', 'subscription_end', 'date_joined',
    )
    list_display_links = ('username', 'email')
    list_filter = (
        'university', 'is_verified', 'verification_status',
        'year_of_study', 'is_email_verified', 'is_active', 'is_staff',
        'subscription_tier',
    )
    search_fields = ('email', 'full_name', 'student_id', 'username', 'phone_number')
    ordering = ('-date_joined',)
    list_per_page = 25
    actions = [approve_users, reject_users]
    date_hierarchy = 'date_joined'

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        (_('Personal Information'), {'fields': ('full_name', 'student_id', 'phone_number', 'profile_photo', 'bio')}),
        (_('Academic Details'), {'fields': ('university', 'course', 'year_of_study')}),
        (_('Identity Verification'), {
            'fields': (
                'is_email_verified', 'is_verified', 'verification_status',
                'id_card_preview', 'selfie_preview',
                'verification_submitted_at', 'verification_reviewed_at',
                'verification_reviewed_by', 'verification_rejection_reason',
            ),
        }),
        (_('Subscription'), {'fields': ('subscription_tier', 'subscription_start', 'subscription_end', 'pro_activated_by')}),
        (_('Permissions'), {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important Dates'), {'classes': ('collapse',), 'fields': ('last_login', 'date_joined', 'last_seen')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'username', 'full_name', 'student_id',
                'university', 'course', 'year_of_study', 'phone_number',
                'password1', 'password2',
            ),
        }),
    )

    readonly_fields = (
        'date_joined', 'last_login', 'last_seen',
        'id_card_preview', 'selfie_preview',
        'verification_submitted_at', 'verification_reviewed_at', 'verification_reviewed_by',
    )

    @admin.display(description='ID Card Photo')
    def id_card_preview(self, obj):
        return _photo_tag(obj.id_card_photo, 'ID Card')

    @admin.display(description='Selfie Photo')
    def selfie_preview(self, obj):
        return _photo_tag(obj.selfie_photo, 'Selfie')


# ---------------------------------------------------------------------------
# EmailVerificationToken admin
# ---------------------------------------------------------------------------

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'is_used', 'is_valid_display')
    list_filter = ('is_used',)
    search_fields = ('user__email', 'user__username', 'token')
    readonly_fields = ('token', 'created_at')
    ordering = ('-created_at',)

    @admin.display(boolean=True, description='Valid?')
    def is_valid_display(self, obj):
        return obj.is_valid()


# ---------------------------------------------------------------------------
# Subscription Payment admin
# ---------------------------------------------------------------------------

@admin.register(SubscriptionPayment)
class SubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = (
        'reference_code', 'user', 'payment_method', 'momo_transaction_id',
        'phone_number_used', 'status', 'submitted_at', 'confirmed_at', 'confirmed_by',
    )
    list_filter = ('status', 'payment_method')
    search_fields = ('reference_code', 'user__email', 'user__full_name', 'momo_transaction_id', 'phone_number_used')
    ordering = ('-submitted_at',)
    readonly_fields = ('reference_code', 'user', 'submitted_at', 'amount')
    list_per_page = 25
    actions = [confirm_payments, reject_payments]
    fieldsets = (
        ('Payment Details', {
            'fields': ('reference_code', 'user', 'amount', 'payment_method',
                       'momo_transaction_id', 'phone_number_used', 'submitted_at'),
        }),
        ('Review', {
            'fields': ('status', 'confirmed_at', 'confirmed_by', 'notes'),
        }),
    )

    def save_model(self, request, obj, form, change):
        """
        When an admin manually edits a payment record and changes status to
        'confirmed' or 'rejected', run the same activation / rejection logic
        that the bulk actions use. This ensures the user's Pro tier is always
        updated regardless of which route the admin took.
        """
        if change and 'status' in form.changed_data:
            # Read the previous status from DB before saving
            try:
                previous_status = SubscriptionPayment.objects.get(pk=obj.pk).status
            except SubscriptionPayment.DoesNotExist:
                previous_status = None

            if obj.status == 'confirmed' and previous_status != 'confirmed':
                # Don't call super() yet — _activate_pro_for_payment calls save() itself
                _activate_pro_for_payment(obj, request.user)
                self.message_user(request, f'Pro activated for {obj.user.display_name}.', django_messages.SUCCESS)
                return  # already saved inside helper

            if obj.status == 'rejected' and previous_status != 'rejected':
                _reject_payment(obj, reason=obj.notes)
                self.message_user(request, f'Payment {obj.reference_code} rejected and user notified.', django_messages.WARNING)
                return  # already saved inside helper

        super().save_model(request, obj, form, change)


# ---------------------------------------------------------------------------
# Pending Verifications — dedicated admin section
# ---------------------------------------------------------------------------

class PendingVerificationProxy(CustomUser):
    """Proxy so 'Pending Verifications' appears as its own section in admin."""
    class Meta:
        proxy = True
        verbose_name = 'Pending Verification'
        verbose_name_plural = 'Pending Verifications'


@admin.register(PendingVerificationProxy)
class PendingVerificationAdmin(admin.ModelAdmin):
    """
    Shows only users with verification_status='pending'.
    Admin can see both photos side-by-side and approve/reject individually
    or in bulk.
    """
    list_display = (
        'full_name', 'email', 'student_id', 'university',
        'id_card_preview', 'selfie_preview', 'verification_submitted_at',
    )
    list_display_links = ('full_name', 'email')
    search_fields = ('email', 'full_name', 'student_id')
    ordering = ('verification_submitted_at',)
    actions = ['approve_selected', 'reject_selected']

    readonly_fields = (
        'full_name', 'email', 'student_id', 'university', 'course', 'year_of_study',
        'verification_submitted_at',
        'id_card_preview', 'selfie_preview',
        'verification_reviewed_at', 'verification_reviewed_by',
    )
    fields = (
        ('full_name', 'email'),
        ('student_id', 'university'),
        ('course', 'year_of_study'),
        'verification_submitted_at',
        ('id_card_preview', 'selfie_preview'),
        'verification_status',
        'is_verified',
        'verification_rejection_reason',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(verification_status='pending')

    @admin.display(description='ID Card')
    def id_card_preview(self, obj):
        return _photo_tag(obj.id_card_photo, 'ID Card')

    @admin.display(description='Selfie')
    def selfie_preview(self, obj):
        return _photo_tag(obj.selfie_photo, 'Selfie')

    def save_model(self, request, obj, form, change):
        """Track who reviewed when the status changes."""
        if change and 'verification_status' in form.changed_data:
            obj.verification_reviewed_at = timezone.now()
            obj.verification_reviewed_by = request.user
            if obj.verification_status == 'verified':
                obj.is_verified = True
            elif obj.verification_status == 'rejected':
                obj.is_verified = False
        super().save_model(request, obj, form, change)

    @admin.action(description='✅ Approve selected verifications')
    def approve_selected(self, request, queryset):
        updated = 0
        for user in queryset:
            user.verification_status = 'verified'
            user.is_verified = True
            user.verification_reviewed_at = timezone.now()
            user.verification_reviewed_by = request.user
            user.save(update_fields=[
                'verification_status', 'is_verified',
                'verification_reviewed_at', 'verification_reviewed_by',
            ])
            updated += 1
        self.message_user(request, f'{updated} verification(s) approved.', django_messages.SUCCESS)

    @admin.action(description='❌ Reject selected — photos unclear')
    def reject_selected(self, request, queryset):
        updated = 0
        for user in queryset:
            user.verification_status = 'rejected'
            user.is_verified = False
            user.verification_reviewed_at = timezone.now()
            user.verification_reviewed_by = request.user
            user.verification_rejection_reason = 'ID card photo or selfie is unclear or unreadable'
            user.save(update_fields=[
                'verification_status', 'is_verified',
                'verification_reviewed_at', 'verification_reviewed_by',
                'verification_rejection_reason',
            ])
            updated += 1
        self.message_user(request, f'{updated} verification(s) rejected.', django_messages.WARNING)

    def has_add_permission(self, request):
        return False  # can't create users from here
