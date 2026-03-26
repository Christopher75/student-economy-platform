from django.shortcuts import render
from django.http import HttpResponse

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

    # Trending: highest view count, strictly excluding anything already in Featured
    featured_pks = [l.pk for l in featured_qs]
    hot_listings = Listing.objects.filter(status='available').exclude(
        pk__in=featured_pks
    ).order_by('-views_count')[:6]

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

def handler404(request, exception):
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    return render(request, 'errors/500.html', status=500)
