"""
URL patterns for the bookings sub-section of the skills app.
Mount this at /bookings/ in the project urls.py with app_name='bookings'.

Example in student_economy/urls.py:
    path('bookings/', include('skills.booking_urls')),
"""
from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    # Booking management
    path("", views.MyBookingsView.as_view(), name="my_bookings"),
    path("<int:pk>/", views.BookingDetailView.as_view(), name="booking_detail"),
    path("<int:pk>/accept/", views.accept_booking, name="accept_booking"),
    path("<int:pk>/decline/", views.decline_booking, name="decline_booking"),
    path("<int:pk>/complete/", views.complete_booking, name="complete_booking"),
    path("<int:pk>/review/", views.leave_review, name="leave_review"),
]
