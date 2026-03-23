from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="notification_list"),
    path("<int:pk>/read/", views.mark_read, name="mark_read"),
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
]
