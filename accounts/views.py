from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.db.models import Count, Q

from .models import EmailVerificationToken
from .forms import RegistrationForm, EmailLoginForm, ProfileEditForm, StudentPasswordChangeForm

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterView(View):
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        form = RegistrationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            # In development (DEBUG=True), auto-verify email so users can log in immediately
            if settings.DEBUG:
                user.is_email_verified = True
                user.verification_status = 'approved'
                user.is_verified = True
            user.save()

            if settings.DEBUG:
                messages.success(
                    request,
                    'Account created successfully! You can now log in.',
                )
                return redirect('accounts:login')

            # Production: send verification email
            token_obj = EmailVerificationToken.objects.create(user=user)
            self._send_verification_email(request, user, token_obj.token)
            messages.success(
                request,
                'Account created! Please check your email to verify your address before logging in.',
            )
            return redirect('accounts:login')

        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})

    @staticmethod
    def _send_verification_email(request, user, token):
        verification_url = request.build_absolute_uri(
            reverse('accounts:verify_email', kwargs={'token': str(token)})
        )
        subject = 'Verify your Student Economy Platform email'
        message = (
            f"Hi {user.display_name},\n\n"
            f"Welcome to the Student Economy Platform!\n\n"
            f"Please click the link below to verify your email address:\n"
            f"{verification_url}\n\n"
            f"This link is valid for 3 days.\n\n"
            f"If you did not register, please ignore this email.\n\n"
            f"— The Student Economy Platform Team"
        )
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception:
            # Don't crash registration if email delivery fails
            pass


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)

    if not token_obj.is_valid():
        messages.error(
            request,
            'This verification link has expired or has already been used. '
            'Please request a new one.',
        )
        return redirect('accounts:login')

    user = token_obj.user
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified. You can log in.')
        return redirect('accounts:login')

    user.is_email_verified = True
    user.save(update_fields=['is_email_verified'])

    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])

    messages.success(
        request,
        'Email verified successfully! You can now log in to your account.',
    )
    return redirect('accounts:login')


def resend_verification(request):
    """Allow a logged-in but unverified user to request a new verification email."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    user = request.user
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('accounts:dashboard')

    # Invalidate old tokens
    EmailVerificationToken.objects.filter(user=user, is_used=False).update(is_used=True)
    token_obj = EmailVerificationToken.objects.create(user=user)
    RegisterView._send_verification_email(request, user, token_obj.token)

    messages.success(request, 'A new verification email has been sent. Please check your inbox.')
    return redirect('accounts:dashboard')


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

class LoginView(View):
    template_name = 'accounts/login.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        form = EmailLoginForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')

        form = EmailLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()

            if not user.is_email_verified:
                messages.warning(
                    request,
                    'Please verify your email address before logging in. '
                    'Check your inbox or <a href="'
                    + reverse('accounts:resend_verification')
                    + '">resend the verification email</a>.',
                )
                return render(request, self.template_name, {'form': form})

            # Handle remember me
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)  # Expire on browser close
            else:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days

            login(request, user)
            messages.success(request, f'Welcome back, {user.display_name}!')

            next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)

        messages.error(request, 'Invalid email or password. Please try again.')
        return render(request, self.template_name, {'form': form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect(settings.LOGOUT_REDIRECT_URL)

    # Allow GET logout too (e.g. from a simple link), but POST is preferred
    def get(self, request):
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
        return redirect(settings.LOGOUT_REDIRECT_URL)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileView(View):
    template_name = 'accounts/profile.html'

    def get(self, request, username):
        profile_user = get_object_or_404(User, username=username)

        # Gather related data — guarded with try/except so missing apps don't break profile
        listings = []
        skills = []
        reviews = []

        try:
            from marketplace.models import Listing
            listings = Listing.objects.filter(
                seller=profile_user, status='active'
            ).order_by('-created_at')[:6]
        except Exception:
            pass

        try:
            from skills.models import SkillListing, Review
            skills = SkillListing.objects.filter(
                provider=profile_user, is_active=True
            ).order_by('-created_at')[:6]
            reviews = Review.objects.filter(
                reviewee=profile_user
            ).select_related('reviewer').order_by('-created_at')[:10]
        except Exception:
            pass

        context = {
            'profile_user': profile_user,
            'listings': listings,
            'skills': skills,
            'reviews': reviews,
            'average_rating': profile_user.get_average_rating(),
            'review_count': profile_user.get_review_count(),
            'trust_score': profile_user.get_trust_score(),
            'is_own_profile': request.user == profile_user,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Edit Profile
# ---------------------------------------------------------------------------

@method_decorator(login_required, name='dispatch')
class EditProfileView(View):
    template_name = 'accounts/edit_profile.html'

    def get(self, request):
        form = ProfileEditForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('accounts:profile', username=request.user.username)

        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    template_name = 'accounts/dashboard.html'

    def get(self, request):
        user = request.user
        stats = {}

        try:
            from marketplace.models import Listing
            stats['active_listings'] = Listing.objects.filter(
                seller=user, status='active'
            ).count()
            stats['sold_listings'] = Listing.objects.filter(
                seller=user, status='sold'
            ).count()
        except Exception:
            stats['active_listings'] = 0
            stats['sold_listings'] = 0

        try:
            from skills.models import SkillListing, SkillBooking
            stats['active_skills'] = SkillListing.objects.filter(
                provider=user, is_active=True
            ).count()
            stats['pending_bookings'] = SkillBooking.objects.filter(
                Q(provider=user) | Q(client=user),
                status='pending',
            ).count()
            stats['completed_bookings'] = SkillBooking.objects.filter(
                Q(provider=user) | Q(client=user),
                status='completed',
            ).count()
        except Exception:
            stats['active_skills'] = 0
            stats['pending_bookings'] = 0
            stats['completed_bookings'] = 0

        try:
            from messaging.models import Message
            stats['unread_messages'] = Message.objects.filter(
                recipient=user, is_read=False
            ).count()
        except Exception:
            stats['unread_messages'] = 0

        try:
            from notifications.models import Notification
            stats['unread_notifications'] = Notification.objects.filter(
                recipient=user, is_read=False
            ).count()
        except Exception:
            stats['unread_notifications'] = 0

        # Recent listings
        recent_listings = []
        try:
            from marketplace.models import Listing
            recent_listings = Listing.objects.filter(seller=user).order_by('-created_at')[:5]
        except Exception:
            pass

        # Recent bookings
        recent_bookings = []
        try:
            from skills.models import SkillBooking
            recent_bookings = SkillBooking.objects.filter(
                Q(provider=user) | Q(client=user)
            ).select_related('skill', 'client', 'provider').order_by('-created_at')[:5]
        except Exception:
            pass

        context = {
            'stats': stats,
            'recent_listings': recent_listings,
            'recent_bookings': recent_bookings,
            'average_rating': user.get_average_rating(),
            'review_count': user.get_review_count(),
            'trust_score': user.get_trust_score(),
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Password Change (custom styled)
# ---------------------------------------------------------------------------

@method_decorator(login_required, name='dispatch')
class PasswordChangeView(View):
    template_name = 'accounts/password_change.html'

    def get(self, request):
        form = StudentPasswordChangeForm(user=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = StudentPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Re-authenticate so the session doesn't expire
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, form.user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('accounts:dashboard')

        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})
