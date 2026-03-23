from django.urls import path

from . import views

app_name = "skills"

urlpatterns = [
    # Skill offerings
    path("", views.SkillListView.as_view(), name="skill_list"),
    path("create/", views.skill_create, name="skill_create"),
    path("<int:pk>/", views.SkillDetailView.as_view(), name="skill_detail"),
    path("<int:pk>/edit/", views.skill_edit, name="skill_edit"),
    path("<int:pk>/delete/", views.skill_delete, name="skill_delete"),

    # Portfolio image deletion
    path("portfolio/<int:pk>/delete/", views.delete_portfolio_item, name="delete_portfolio_item"),

    # Booking request (initiated from skill detail page)
    path("<int:skill_pk>/book/", views.booking_request, name="booking_request"),
]
