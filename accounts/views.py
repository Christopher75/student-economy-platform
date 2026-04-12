import json
import logging
import os
from datetime import timedelta

logger = logging.getLogger(__name__)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordResetView as BasePasswordResetView
from django.contrib import messages as django_messages
from django.contrib import messages
from django.views import View
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
from django.db.models import Count, Q
from django.http import JsonResponse, Http404, FileResponse, HttpResponse
from django.template.loader import render_to_string

from .models import EmailVerificationToken, EmailOTPVerification, SubscriptionPayment, _generate_otp, _hash_otp
from .forms import (
    RegistrationForm, EmailLoginForm, ProfileEditForm,
    StudentPasswordChangeForm, IdentityVerificationForm,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# OTP email sending helper
# ---------------------------------------------------------------------------

def _send_otp_email(user, otp_code):
    """Send the 6-digit OTP to the user's email. Returns True on success."""
    subject = 'Verify your Student Economy Platform account'
    context = {
        'user': user,
        'otp_code': otp_code,
    }
    text_body = render_to_string('accounts/emails/otp_email.txt', context)
    html_body = render_to_string('accounts/emails/otp_email.html', context)
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.error('OTP email failed for user %s: %s', user.email, exc, exc_info=True)
        return False


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
            user.is_email_verified = False
            user.verification_status = 'unverified'
            user.is_verified = False
            # Capture registration IP
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if x_forwarded:
                user.registration_ip = x_forwarded.split(',')[0].strip()
            else:
                user.registration_ip = request.META.get('REMOTE_ADDR', '')
            user.save()

            # Create OTP record and send email
            plain_otp = _generate_otp()
            now = timezone.now()
            EmailOTPVerification.objects.filter(user=user).delete()
            EmailOTPVerification.objects.create(
                user=user,
                otp_hash=_hash_otp(plain_otp),
                otp_created_at=now,
                otp_expires_at=now + timedelta(minutes=15),
            )
            _send_otp_email(user, plain_otp)

            # Store user pk in session so the OTP page knows who is verifying
            request.session['pending_verify_user_id'] = user.pk
            return redirect('accounts:verify_email_otp')

        messages.error(request, 'Please correct the errors below.')
        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# Email OTP Verification
# ---------------------------------------------------------------------------

def verify_email_otp(request):
    """
    GET  — show the 6-digit OTP entry page.
    POST — check the submitted OTP and either verify or reject.
    """
    # Resolve which user is verifying
    user_pk = request.session.get('pending_verify_user_id')
    if not user_pk and request.user.is_authenticated and not request.user.is_email_verified:
        user_pk = request.user.pk

    if not user_pk:
        return redirect('accounts:login')

    user = get_object_or_404(User, pk=user_pk)

    if user.is_email_verified:
        # Already done — if logged in, send to verify-identity; else to login
        if request.user.is_authenticated:
            return redirect('accounts:verify_identity')
        return redirect('accounts:login')

    # Ensure an OTP record exists
    otp_obj, _ = EmailOTPVerification.objects.get_or_create(
        user=user,
        defaults={
            'otp_hash': '',
            'otp_created_at': timezone.now(),
            'otp_expires_at': timezone.now() + timedelta(minutes=15),
        }
    )

    # Mask email: first 2 chars + *** + @domain
    email_parts = user.email.split('@')
    masked_email = email_parts[0][:2] + '***@' + email_parts[1]

    context = {
        'masked_email': masked_email,
        'otp_obj': otp_obj,
        'seconds_until_resend': otp_obj.seconds_until_resend(),
    }

    if request.method == 'GET':
        return render(request, 'accounts/verify_email_otp.html', context)

    # POST — check OTP
    submitted = request.POST.get('otp_code', '').strip()
    if len(submitted) != 6 or not submitted.isdigit():
        context['error'] = 'Please enter the full 6-digit code.'
        return render(request, 'accounts/verify_email_otp.html', context)

    result = otp_obj.check_otp(submitted)

    if result == 'ok':
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        # Clear session marker
        request.session.pop('pending_verify_user_id', None)
        # Log the user in
        if not request.user.is_authenticated:
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
        messages.success(request, 'Your email is verified. Welcome to the platform.')
        return redirect('accounts:verify_identity')

    if result == 'locked':
        until = otp_obj.locked_until
        context['error'] = (
            f'Too many incorrect attempts. Please wait 30 minutes or request a new code.'
        )
    elif result == 'expired':
        context['error'] = 'This code has expired. Request a new one below.'
    elif result == 'wrong':
        remaining = otp_obj.remaining_attempts()
        if remaining == 0:
            context['error'] = (
                'Too many incorrect attempts. Your account is temporarily locked for 30 minutes.'
            )
        else:
            context['error'] = (
                f'Incorrect code. {remaining} attempt{"s" if remaining != 1 else ""} remaining before your account is temporarily locked.'
            )
    else:
        context['error'] = 'This code is no longer valid. Please request a new one.'

    context['otp_obj'] = otp_obj
    context['seconds_until_resend'] = otp_obj.seconds_until_resend()
    return render(request, 'accounts/verify_email_otp.html', context)


def resend_otp(request):
    """POST-only: generate a new OTP and resend. Returns JSON."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Method not allowed'}, status=405)

    user_pk = request.session.get('pending_verify_user_id')
    if not user_pk and request.user.is_authenticated:
        user_pk = request.user.pk

    if not user_pk:
        return JsonResponse({'ok': False, 'error': 'Session expired. Please register again.'}, status=400)

    user = get_object_or_404(User, pk=user_pk)

    if user.is_email_verified:
        return JsonResponse({'ok': False, 'error': 'Email is already verified.'}, status=400)

    otp_obj = getattr(user, 'email_otp', None)
    if not otp_obj:
        return JsonResponse({'ok': False, 'error': 'No verification record found.'}, status=400)

    if otp_obj.resend_count >= 5:
        return JsonResponse({
            'ok': False,
            'error': 'You have requested too many codes. Please contact support if you are having trouble.',
        }, status=429)

    if not otp_obj.can_resend():
        wait = otp_obj.seconds_until_resend()
        return JsonResponse({'ok': False, 'error': f'Please wait {wait} seconds before requesting a new code.'}, status=429)

    plain_otp = otp_obj.refresh_otp()
    _send_otp_email(user, plain_otp)

    return JsonResponse({
        'ok': True,
        'resend_count': otp_obj.resend_count,
        'seconds_until_next': 60,
    })


# Legacy link-based email verification (kept for backward compatibility)
def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)
    if not token_obj.is_valid():
        messages.error(request, 'This verification link has expired or has already been used.')
        return redirect('accounts:login')
    user = token_obj.user
    if user.is_email_verified:
        messages.info(request, 'Your email is already verified. You can log in.')
        return redirect('accounts:login')
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified'])
    token_obj.is_used = True
    token_obj.save(update_fields=['is_used'])
    messages.success(request, 'Email verified! You can now log in.')
    return redirect('accounts:login')


def resend_verification(request):
    """Legacy resend — now redirects to OTP page."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    if request.user.is_email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('accounts:dashboard')
    request.session['pending_verify_user_id'] = request.user.pk
    return redirect('accounts:verify_email_otp')


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

        # Increment profile view count (don't count own views)
        if request.user != profile_user:
            User.objects.filter(pk=profile_user.pk).update(
                profile_view_count=profile_user.profile_view_count + 1
            )

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


# ---------------------------------------------------------------------------
# Subscription / Pro Upgrade
# ---------------------------------------------------------------------------

@login_required
def upgrade_view(request):
    """Show Free vs Pro comparison page and start payment if POST."""
    user = request.user
    # If already Pro, redirect to analytics
    if user.is_pro():
        return redirect('accounts:analytics')
    return render(request, 'accounts/upgrade.html', {
        'user': user,
        'mtn_number': settings.PLATFORM_MTN_NUMBER,
        'airtel_number': settings.PLATFORM_AIRTEL_NUMBER,
    })


@login_required
def initiate_payment(request):
    """Create a SubscriptionPayment record and redirect to payment instructions."""
    if request.method != 'POST':
        return redirect('accounts:upgrade')
    user = request.user
    if user.is_pro():
        messages.info(request, 'You already have an active Pro subscription.')
        return redirect('accounts:analytics')
    # Check for existing pending payment
    existing = SubscriptionPayment.objects.filter(user=user, status='pending').first()
    if existing:
        return redirect('accounts:payment_detail', ref=existing.reference_code)
    payment = SubscriptionPayment.objects.create(user=user)
    return redirect('accounts:payment_detail', ref=payment.reference_code)


@login_required
def payment_detail(request, ref):
    """Show payment instructions and allow submitting MoMo transaction ID."""
    payment = get_object_or_404(SubscriptionPayment, reference_code=ref, user=request.user)

    if request.method == 'POST' and payment.status == 'pending':
        payment_method = request.POST.get('payment_method', '')
        momo_transaction_id = request.POST.get('momo_transaction_id', '').strip()
        phone_number_used = request.POST.get('phone_number_used', '').strip()

        valid_methods = [c[0] for c in SubscriptionPayment.PAYMENT_METHOD_CHOICES]
        if payment_method not in valid_methods:
            messages.error(request, 'Please select a valid payment method.')
        elif not momo_transaction_id:
            messages.error(request, 'Please enter your MoMo transaction ID.')
        elif not phone_number_used:
            messages.error(request, 'Please enter the phone number you sent from.')
        else:
            payment.payment_method = payment_method
            payment.momo_transaction_id = momo_transaction_id
            payment.phone_number_used = phone_number_used
            payment.save(update_fields=['payment_method', 'momo_transaction_id', 'phone_number_used'])
            messages.success(request, 'Payment details submitted! We will confirm within 24 hours.')
            return redirect('accounts:payment_success', ref=payment.reference_code)

    return render(request, 'accounts/payment.html', {
        'payment': payment,
        'mtn_number': settings.PLATFORM_MTN_NUMBER,
        'airtel_number': settings.PLATFORM_AIRTEL_NUMBER,
    })


@login_required
def payment_success(request, ref):
    payment = get_object_or_404(SubscriptionPayment, reference_code=ref, user=request.user)
    return render(request, 'accounts/payment_success.html', {'payment': payment})


@login_required
def payment_history(request):
    payments = SubscriptionPayment.objects.filter(user=request.user)
    return render(request, 'accounts/payment_history.html', {'payments': payments})


@login_required
def analytics_view(request):
    """Pro analytics dashboard. Free users see a locked preview."""
    user = request.user
    is_pro = user.is_pro()

    listing_data = {}
    skill_data = {}
    if is_pro:
        try:
            from marketplace.models import Listing
            from django.db.models import Sum, Avg, Count
            all_listings = Listing.objects.filter(seller=user)
            available = all_listings.filter(status='available')
            sold = all_listings.filter(status='sold')

            total_views = all_listings.aggregate(t=Sum('views_count'))['t'] or 0
            total_sold_value = sold.aggregate(t=Sum('price'))['t'] or 0

            listing_data = {
                'total_views': total_views,
                'available_count': available.count(),
                'sold_count': sold.count(),
                'total_sold_value': total_sold_value,
                'top_listing': all_listings.order_by('-views_count').first(),
                'avg_price': all_listings.aggregate(a=Avg('price'))['a'] or 0,
                # Views-to-listing efficiency: avg views per listing
                'avg_views_per_listing': round(total_views / max(all_listings.count(), 1), 1),
            }
        except Exception:
            pass
        try:
            from skills.models import SkillOffering, SkillBooking
            from django.db.models import Q
            skills = SkillOffering.objects.filter(provider=user)
            all_bookings = SkillBooking.objects.filter(provider=user)
            completed = all_bookings.filter(status='completed').count()
            accepted = all_bookings.filter(status__in=['accepted', 'completed']).count()
            total_requests = all_bookings.count()

            skill_data = {
                'total_bookings': total_requests,
                'completed_bookings': completed,
                'acceptance_rate': round((accepted / max(total_requests, 1)) * 100),
                'top_skill': skills.order_by('-views_count').first(),
                'active_skills': skills.filter(status='active').count(),
                'total_skill_views': skills.aggregate(t=Sum('views_count'))['t'] or 0,
            }
        except Exception:
            pass

    return render(request, 'accounts/analytics.html', {
        'is_pro': is_pro,
        'listing_data': listing_data,
        'skill_data': skill_data,
        'profile_views': user.profile_view_count,
        'trust_score': user.trust_score,
    })


# ---------------------------------------------------------------------------
# Admin Panel (staff-only)
# ---------------------------------------------------------------------------

def _staff_required(view_func):
    """Redirect unauthenticated or non-staff users to home."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def _payments_required(view_func):
    """Allow only users with the can_manage_payments permission (or superuser)."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('home')
        if request.user.is_superuser or request.user.has_perm('accounts.can_manage_payments'):
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper


def _verification_required(view_func):
    """Allow only users with the can_review_verifications permission (or superuser)."""
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('home')
        if request.user.is_superuser or request.user.has_perm('accounts.can_review_verifications'):
            return view_func(request, *args, **kwargs)
        return redirect('home')
    return wrapper


@_payments_required
def admin_payments_list(request):
    """Admin view: list all pending payments for review."""
    status_filter = request.GET.get('status', 'pending')
    payments = SubscriptionPayment.objects.select_related('user')
    if status_filter in ('pending', 'confirmed', 'rejected'):
        payments = payments.filter(status=status_filter)
    return render(request, 'admin_panel/payments.html', {
        'payments': payments,
        'status_filter': status_filter,
    })


@_payments_required
def admin_payment_confirm(request, pk):
    """Admin: confirm a payment → activate Pro for 30 days."""
    if request.method != 'POST':
        return redirect('accounts:admin_payments')
    payment = get_object_or_404(SubscriptionPayment, pk=pk)
    if payment.status != 'pending':
        messages.warning(request, 'This payment has already been processed.')
        return redirect('accounts:admin_payments')

    from django.utils import timezone
    from datetime import timedelta, date
    payment.status = 'confirmed'
    payment.confirmed_at = timezone.now()
    payment.confirmed_by = request.user
    payment.save(update_fields=['status', 'confirmed_at', 'confirmed_by'])

    user = payment.user
    user.subscription_tier = 'pro'
    user.subscription_start = date.today()
    user.subscription_end = date.today() + timedelta(days=30)
    user.pro_activated_by = 'manual'
    user.save(update_fields=['subscription_tier', 'subscription_start', 'subscription_end', 'pro_activated_by'])

    # Notify user
    try:
        from notifications.models import Notification
        Notification.create(
            user=user,
            notification_type='pro_activated',
            title='Pro Subscription Activated!',
            message=f'Your Pro Seller subscription is now active until {user.subscription_end.strftime("%d %b %Y")}. Enjoy unlimited listings, skills, messages and more!',
            action_url=reverse('accounts:analytics'),
        )
    except Exception:
        pass

    messages.success(request, f'Pro activated for {user.display_name} until {user.subscription_end}.')
    return redirect('accounts:admin_payments')


@_payments_required
def admin_payment_reject(request, pk):
    """Admin: reject a payment with an optional reason."""
    if request.method != 'POST':
        return redirect('accounts:admin_payments')
    payment = get_object_or_404(SubscriptionPayment, pk=pk)
    if payment.status != 'pending':
        messages.warning(request, 'This payment has already been processed.')
        return redirect('accounts:admin_payments')

    reason = request.POST.get('reason', '').strip()
    payment.status = 'rejected'
    payment.notes = reason
    payment.save(update_fields=['status', 'notes'])

    # Notify user
    try:
        from notifications.models import Notification
        Notification.create(
            user=payment.user,
            notification_type='payment_rejected',
            title='Payment Not Confirmed',
            message=f'Your Pro upgrade payment ({payment.reference_code}) was not confirmed.{" Reason: " + reason if reason else ""} Please contact support or try again.',
            action_url=reverse('accounts:upgrade'),
        )
    except Exception:
        pass

    messages.success(request, f'Payment {payment.reference_code} rejected.')
    return redirect('accounts:admin_payments')


# ---------------------------------------------------------------------------
# Identity (Document) Verification
# ---------------------------------------------------------------------------

@login_required
def verify_identity(request):
    """
    Show the two-photo upload form. Only accessible to email-verified users
    who have not yet submitted or were rejected.
    """
    user = request.user

    if not user.is_email_verified:
        return redirect('accounts:verify_email_otp')

    # Already submitted or approved — show status page
    if user.verification_status == 'pending':
        return render(request, 'accounts/verify_identity_submitted.html', {'pending': True})
    if user.verification_status == 'verified':
        return redirect('accounts:dashboard')

    # unverified or rejected — show upload form
    form = IdentityVerificationForm()
    rejected = user.verification_status == 'rejected'

    if request.method == 'POST':
        form = IdentityVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            user.id_card_photo = form.cleaned_data['id_card_photo']
            user.selfie_photo = form.cleaned_data['selfie_photo']
            user.verification_status = 'pending'
            user.verification_submitted_at = timezone.now()
            user.verification_rejection_reason = ''
            user.save(update_fields=[
                'id_card_photo', 'selfie_photo',
                'verification_status', 'verification_submitted_at',
                'verification_rejection_reason',
            ])
            # Notify admins
            try:
                from notifications.models import Notification
                for admin in User.objects.filter(is_staff=True):
                    Notification.create(
                        user=admin,
                        notification_type='info',
                        title='New Verification Submission',
                        message=f'{user.display_name} has submitted identity documents for review.',
                        action_url=reverse('accounts:admin_verification'),
                    )
            except Exception:
                pass
            return render(request, 'accounts/verify_identity_submitted.html', {'pending': True})

    return render(request, 'accounts/verify_identity.html', {
        'form': form,
        'rejected': rejected,
        'rejection_reason': user.verification_rejection_reason,
    })


@_verification_required
def serve_verification_photo(request, photo_type, pk):
    """Serve a verification photo securely — staff only."""
    user = get_object_or_404(User, pk=pk)
    if photo_type == 'id_card':
        field = user.id_card_photo
    elif photo_type == 'selfie':
        field = user.selfie_photo
    else:
        raise Http404

    if not field:
        raise Http404

    # Cloudinary: field.url already returns the CDN URL — redirect directly
    cloudinary_configured = bool(getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''))
    if cloudinary_configured:
        try:
            return redirect(field.url)
        except Exception:
            raise Http404

    # Local storage — serve via FileResponse
    try:
        import mimetypes
        path = os.path.join(settings.MEDIA_ROOT, field.name)
        content_type, _ = mimetypes.guess_type(path)
        return FileResponse(open(path, 'rb'), content_type=content_type or 'image/jpeg')
    except FileNotFoundError:
        raise Http404


# ---------------------------------------------------------------------------
# Admin Verification Review
# ---------------------------------------------------------------------------

@_verification_required
def admin_verification_list(request):
    """List all pending verification submissions side-by-side."""
    status_filter = request.GET.get('status', 'pending')
    users = User.objects.exclude(verification_status='unverified').select_related()
    if status_filter in ('pending', 'verified', 'rejected'):
        users = users.filter(verification_status=status_filter)
    return render(request, 'admin_panel/verification.html', {
        'users': users,
        'status_filter': status_filter,
        'status_choices': [('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')],
    })


@_verification_required
def admin_verification_approve(request, pk):
    """Approve a verification submission."""
    if request.method != 'POST':
        return redirect('accounts:admin_verification')

    user = get_object_or_404(User, pk=pk)
    user.verification_status = 'verified'
    user.is_verified = True
    user.verification_reviewed_at = timezone.now()
    user.verification_reviewed_by = request.user
    user.save(update_fields=[
        'verification_status', 'is_verified',
        'verification_reviewed_at', 'verification_reviewed_by',
    ])

    # In-app notification
    try:
        from notifications.models import Notification
        Notification.create(
            user=user,
            notification_type='verification_approved',
            title='Identity Verified!',
            message=(
                'Your identity has been verified. Your Verified Student badge is now active '
                'on your profile and all your listings.'
            ),
            action_url=reverse('accounts:profile', kwargs={'username': user.username}),
        )
    except Exception:
        pass

    # Email notification
    try:
        subject = 'You are now a Verified Student'
        ctx = {'user': user}
        text_body = render_to_string('accounts/emails/identity_verified.txt', ctx)
        html_body = render_to_string('accounts/emails/identity_verified.html', ctx)
        msg = EmailMultiAlternatives(
            subject=subject, body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass

    messages.success(request, f'{user.display_name} is now a Verified Student.')
    return redirect('accounts:admin_verification')


@_verification_required
def admin_verification_reject(request, pk):
    """Reject a verification submission with a reason."""
    if request.method != 'POST':
        return redirect('accounts:admin_verification')

    user = get_object_or_404(User, pk=pk)
    reason = request.POST.get('reason', '').strip()
    notes = request.POST.get('notes', '').strip()
    full_reason = reason + (f' — {notes}' if notes else '')

    user.verification_status = 'rejected'
    user.is_verified = False
    user.verification_reviewed_at = timezone.now()
    user.verification_reviewed_by = request.user
    user.verification_rejection_reason = full_reason
    user.save(update_fields=[
        'verification_status', 'is_verified',
        'verification_reviewed_at', 'verification_reviewed_by',
        'verification_rejection_reason',
    ])

    # In-app notification
    try:
        from notifications.models import Notification
        Notification.create(
            user=user,
            notification_type='verification_rejected',
            title='Identity Verification Not Approved',
            message=(
                f'Your identity verification was not approved. Reason: {full_reason}. '
                'Please resubmit with clearer photos. If you need help, contact support.'
            ),
            action_url=reverse('accounts:verify_identity'),
        )
    except Exception:
        pass

    # Email
    try:
        subject = 'Your identity verification was not approved'
        ctx = {'user': user, 'reason': full_reason}
        text_body = render_to_string('accounts/emails/identity_rejected.txt', ctx)
        html_body = render_to_string('accounts/emails/identity_rejected.html', ctx)
        msg = EmailMultiAlternatives(
            subject=subject, body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL, to=[user.email],
        )
        msg.attach_alternative(html_body, 'text/html')
        msg.send(fail_silently=True)
    except Exception:
        pass

    messages.warning(request, f'Verification rejected for {user.display_name}.')
    return redirect('accounts:admin_verification')
