from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
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

            # Production: attempt to send verification email
            token_obj = EmailVerificationToken.objects.create(user=user)
            email_sent = self._send_verification_email(request, user, token_obj.token)

            if email_sent:
                messages.success(
                    request,
                    'Account created! Please check your email to verify your address before logging in.',
                )
            else:
                # Email failed — auto-verify so the user can still log in
                user.is_email_verified = True
                user.verification_status = 'approved'
                user.is_verified = True
                user.save(update_fields=['is_email_verified', 'verification_status', 'is_verified'])
                messages.success(
                    request,
                    'Account created successfully! You can now log in.',
                )
            return redirect('accounts:login')

        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})

    @staticmethod
    def _send_verification_email(request, user, token):
        """Returns True if email was sent successfully, False otherwise."""
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
            return True
        except BaseException:
            # Catches SMTP errors, timeouts, and worker signals
            return False


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

        user_listings = []
        user_skills = []
        user_reviews = []

        try:
            from marketplace.models import Listing
            user_listings = Listing.objects.filter(
                seller=profile_user, status='available'
            ).order_by('-created_at')[:6]
        except Exception:
            pass

        try:
            from skills.models import SkillOffering, Review
            user_skills = SkillOffering.objects.filter(
                provider=profile_user, status='active'
            ).order_by('-created_at')[:6]
            user_reviews = Review.objects.filter(
                reviewee=profile_user
            ).select_related('reviewer').order_by('-created_at')[:10]
        except Exception:
            pass

        context = {
            'profile_user': profile_user,
            'user_listings': user_listings,
            'user_skills': user_skills,
            'user_reviews': user_reviews,
            'listings_count': len(user_listings),
            'skills_count': len(user_skills),
            'reviews_count': len(user_reviews),
            'average_rating': profile_user.get_average_rating(),
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

        active_listings_count = 0
        sold_count = 0
        active_skills_count = 0
        incoming_pending = 0  # requests sent TO me as provider
        outgoing_pending = 0  # requests I sent as client
        completed_bookings_count = 0

        try:
            from marketplace.models import Listing
            active_listings_count = Listing.objects.filter(seller=user, status='available').count()
            sold_count = Listing.objects.filter(seller=user, status='sold').count()
        except Exception:
            pass

        try:
            from skills.models import SkillOffering, SkillBooking
            active_skills_count = SkillOffering.objects.filter(provider=user, status='active').count()
            incoming_pending = SkillBooking.objects.filter(provider=user, status='pending').count()
            outgoing_pending = SkillBooking.objects.filter(client=user, status='pending').count()
            completed_bookings_count = SkillBooking.objects.filter(
                Q(provider=user) | Q(client=user), status='completed'
            ).count()
        except Exception:
            pass

        recent_listings = []
        try:
            from marketplace.models import Listing
            recent_listings = Listing.objects.filter(seller=user).order_by('-created_at')[:5]
        except Exception:
            pass

        recent_bookings = []
        incoming_pending_bookings = []
        try:
            from skills.models import SkillBooking
            recent_bookings = SkillBooking.objects.filter(
                Q(provider=user) | Q(client=user)
            ).select_related('skill', 'client', 'provider').order_by('-created_at')[:5]
            incoming_pending_bookings = SkillBooking.objects.filter(
                provider=user, status='pending'
            ).select_related('skill', 'client').order_by('-created_at')[:5]
        except Exception:
            pass

        context = {
            'active_listings_count': active_listings_count,
            'sold_count': sold_count,
            'active_skills_count': active_skills_count,
            'pending_bookings_count': incoming_pending + outgoing_pending,
            'incoming_pending_count': incoming_pending,
            'outgoing_pending_count': outgoing_pending,
            'completed_bookings_count': completed_bookings_count,
            'recent_listings': recent_listings,
            'recent_bookings': recent_bookings,
            'incoming_pending_bookings': incoming_pending_bookings,
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


# ---------------------------------------------------------------------------
# Password Reset (custom — catches SMTP errors so they don't cause 500)
# ---------------------------------------------------------------------------

class SafePasswordResetView(BasePasswordResetView):
    """Wraps Django's PasswordResetView to handle email-sending failures gracefully."""
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/emails/password_reset_email.txt'
    html_email_template_name = 'accounts/emails/password_reset_email.html'
    subject_template_name = 'accounts/emails/password_reset_subject.txt'
    success_url = '/accounts/password-reset/sent/'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except Exception:
            # SMTP misconfiguration or connection error — still redirect to
            # "sent" page so users don't see a 500 error.
            return redirect(self.success_url)
