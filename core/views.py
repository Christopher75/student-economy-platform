from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    """Dynamic homepage showing featured listings, skill offerings, stats"""
    from marketplace.models import Listing, Category
    from skills.models import SkillOffering, SkillCategory
    from accounts.models import CustomUser

    context = {
        'featured_listings': Listing.objects.filter(status='available', is_featured=True)[:6],
        'recent_listings': Listing.objects.filter(status='available').order_by('-created_at')[:6],
        'hot_listings': Listing.objects.filter(status='available').order_by('-views_count')[:6],
        'featured_skills': SkillOffering.objects.filter(status='active', is_featured=True)[:6],
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
