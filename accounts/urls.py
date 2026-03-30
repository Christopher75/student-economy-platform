from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings

from . import views
from .views import SafePasswordResetView
from .forms import StudentPasswordChangeForm

app_name = 'accounts'

# Custom styled password-reset views reuse Django's built-in logic but point at
# our own templates (templates/accounts/password_reset_*.html).
password_reset_patterns = [
    path(
        'password-reset/',
        SafePasswordResetView.as_view(),
        name='password_reset',
    ),
    path(
        'password-reset/sent/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url='/accounts/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),

    # Email verification
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Profile — edit must come BEFORE the <str:username> catch-all
    path('profile/edit/', views.EditProfileView.as_view(), name='edit_profile'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),

    # Dashboard & analytics
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('analytics/', views.analytics_view, name='analytics'),

    # Pro subscription
    path('upgrade/', views.upgrade_view, name='upgrade'),
    path('upgrade/start/', views.initiate_payment, name='initiate_payment'),
    path('payment/<str:ref>/', views.payment_detail, name='payment_detail'),
    path('payment/<str:ref>/success/', views.payment_success, name='payment_success'),
    path('payment/history/', views.payment_history, name='payment_history'),

    # Admin panel — payments
    path('admin-panel/payments/', views.admin_payments_list, name='admin_payments'),
    path('admin-panel/payments/<int:pk>/confirm/', views.admin_payment_confirm, name='admin_payment_confirm'),
    path('admin-panel/payments/<int:pk>/reject/', views.admin_payment_reject, name='admin_payment_reject'),

    # Password change (requires login)
    path('password-change/', views.PasswordChangeView.as_view(), name='password_change'),

    # Password reset (uses Django built-ins)
    *password_reset_patterns,
]
