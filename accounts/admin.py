from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages as django_messages

from .models import CustomUser, EmailVerificationToken


# ---------------------------------------------------------------------------
# Custom actions
# ---------------------------------------------------------------------------

@admin.action(description='Approve selected students (set verification to Approved)')
def approve_users(modeladmin, request, queryset):
    updated = queryset.update(verification_status='approved', is_verified=True)
    modeladmin.message_user(
        request,
        f'{updated} student(s) have been approved.',
        django_messages.SUCCESS,
    )


@admin.action(description='Reject selected students (set verification to Rejected)')
def reject_users(modeladmin, request, queryset):
    updated = queryset.update(verification_status='rejected', is_verified=False)
    modeladmin.message_user(
        request,
        f'{updated} student(s) have been rejected.',
        django_messages.WARNING,
    )


# ---------------------------------------------------------------------------
# CustomUser admin
# ---------------------------------------------------------------------------

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    # --- List view ---
    list_display = (
        'username',
        'email',
        'full_name',
        'university',
        'verification_status',
        'is_verified',
        'is_email_verified',
        'year_of_study',
        'date_joined',
        'last_seen',
    )
    list_display_links = ('username', 'email')
    list_filter = (
        'university',
        'is_verified',
        'verification_status',
        'year_of_study',
        'is_email_verified',
        'is_active',
        'is_staff',
    )
    search_fields = ('email', 'full_name', 'student_id', 'username', 'phone_number')
    ordering = ('-date_joined',)
    list_per_page = 25
    actions = [approve_users, reject_users]
    date_hierarchy = 'date_joined'

    # --- Detail / change view ---
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'password'),
        }),
        (_('Personal Information'), {
            'fields': (
                'full_name', 'student_id', 'phone_number',
                'profile_photo', 'bio',
            ),
        }),
        (_('Academic Details'), {
            'fields': ('university', 'course', 'year_of_study'),
        }),
        (_('Verification & Trust'), {
            'fields': (
                'is_email_verified', 'is_verified', 'verification_status',
                'reputation_score',
            ),
        }),
        (_('Activity'), {
            'fields': ('last_seen',),
        }),
        (_('Permissions'), {
            'classes': ('collapse',),
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            ),
        }),
        (_('Important Dates'), {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined'),
        }),
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

    readonly_fields = ('date_joined', 'last_login', 'last_seen', 'reputation_score')


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
