from django.shortcuts import render, redirect
from django.contrib import messages

from .models import SupportTicket


def home(request):
    """Dynamic homepage showing featured listings, skill offerings, stats"""
    from marketplace.models import Listing, Category
    from skills.models import SkillOffering, SkillCategory
    from accounts.models import CustomUser

    # Featured listings: explicitly marked ones first, then pad with newest
    featured_qs = list(Listing.objects.filter(status='available', is_featured=True).order_by('-created_at')[:6])
    if len(featured_qs) < 6:
        pad = Listing.objects.filter(status='available', is_featured=False).order_by('-created_at')[:6 - len(featured_qs)]
        featured_qs = featured_qs + list(pad)

    # Trending: highest view count — different ordering from Featured guarantees
    # they never appear in the same order, even if an item ranks highly in both
    hot_listings = Listing.objects.filter(status='available').order_by('-views_count', '-created_at')[:6]

    # Featured skills: same logic
    featured_skills_qs = list(SkillOffering.objects.filter(status='active', is_featured=True).order_by('-created_at')[:6])
    if len(featured_skills_qs) < 6:
        pad = SkillOffering.objects.filter(status='active', is_featured=False).order_by('-created_at')[:6 - len(featured_skills_qs)]
        featured_skills_qs = featured_skills_qs + list(pad)

    context = {
        'featured_listings': featured_qs,
        'hot_listings': hot_listings,
        'featured_skills': featured_skills_qs,
        'recent_skills': SkillOffering.objects.filter(status='active').order_by('-created_at')[:6],
        'marketplace_categories': Category.objects.all().order_by('order'),
        'skill_categories': SkillCategory.objects.all().order_by('order'),
        'total_users': CustomUser.objects.filter(is_verified=True).count(),
        'total_listings': Listing.objects.filter(status='available').count(),
        'total_skills': SkillOffering.objects.filter(status='active').count(),
    }
    return render(request, 'home.html', context)

def ticket_detail(request, pk):
    """
    Ticket thread page — user sees their original message + all replies.
    Logged-in owner can also post follow-up messages.
    """
    from django.shortcuts import get_object_or_404
    from .models import SupportReply

    ticket = get_object_or_404(SupportTicket, pk=pk)

    # Security: only the ticket owner (matched by user FK or email) can view
    is_owner = False
    if request.user.is_authenticated:
        if ticket.user == request.user or ticket.email == request.user.email:
            is_owner = True
    if not is_owner and not (request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)):
        messages.error(request, 'You do not have permission to view this ticket.')
        return redirect('contact')

    # Mark admin replies as read
    ticket.replies.filter(is_admin_reply=True, read_by_user=False).update(read_by_user=True)

    if request.method == 'POST':
        reply_message = request.POST.get('reply_message', '').strip()
        if not reply_message:
            messages.error(request, 'Please enter a message.')
        elif ticket.status == 'closed':
            messages.warning(request, 'This ticket is closed. Please open a new one.')
        else:
            SupportReply.objects.create(
                ticket=ticket,
                sent_by=request.user if request.user.is_authenticated else None,
                message=reply_message,
                is_admin_reply=False,
                read_by_user=True,
            )
            # Reopen if it was resolved
            if ticket.status == 'resolved':
                ticket.status = 'in_progress'
                ticket.save(update_fields=['status'])
            messages.success(request, 'Your reply has been sent.')
            return redirect('ticket_detail', pk=ticket.pk)

    return render(request, 'core/ticket_detail.html', {
        'ticket': ticket,
        'replies': ticket.replies.all(),
    })


def contact_view(request):
    """Public contact / support form. Works for logged-in and anonymous users."""
    CATEGORY_CHOICES = SupportTicket.CATEGORY_CHOICES

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        category = request.POST.get('category', 'other')
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        valid_cats = [c[0] for c in CATEGORY_CHOICES]
        if not name or not email or not subject or not message:
            messages.error(request, 'Please fill in all required fields.')
        elif category not in valid_cats:
            messages.error(request, 'Please select a valid category.')
        else:
            ticket = SupportTicket.objects.create(
                user=request.user if request.user.is_authenticated else None,
                name=name,
                email=email,
                category=category,
                subject=subject,
                message=message,
            )
            messages.success(
                request,
                f'Your message has been received (Ticket #{ticket.pk}). '
                'We\'ll respond within 24–48 hours. '
                'You can track replies on your ticket page.'
            )
            return redirect('ticket_detail', pk=ticket.pk)

    # Pre-fill from logged-in user
    initial_name = ''
    initial_email = ''
    my_tickets = []
    if request.user.is_authenticated:
        initial_name = request.user.display_name
        initial_email = request.user.email
        my_tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')[:5]

    return render(request, 'core/contact.html', {
        'category_choices': CATEGORY_CHOICES,
        'initial_name': initial_name,
        'initial_email': initial_email,
        'my_tickets': my_tickets,
    })


def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)
