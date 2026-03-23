from django.urls import path

from . import views

app_name = "messaging"

urlpatterns = [
    path("", views.InboxView.as_view(), name="inbox"),
    path("<int:pk>/", views.ConversationView.as_view(), name="conversation"),
    path("start/<str:username>/", views.start_conversation, name="start"),
    path(
        "start/listing/<int:listing_pk>/",
        views.start_conversation_for_listing,
        name="start_for_listing",
    ),
    path(
        "start/skill/<int:skill_pk>/",
        views.start_conversation_for_skill,
        name="start_for_skill",
    ),
]
