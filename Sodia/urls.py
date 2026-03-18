"""
URL configuration for Sodia project.

This file defines paths that are accessible on the website, except for static files.
This file is at the project root, so it doesn't define individual views,
but includes paths from other apps in the project.
"""

from django.urls import path, include

handler404 = "Sodia.views.handle404"  # handle 404 errors
handler500 = "Sodia.views.handle500"  # handle 500 errors
# CSRF failure error view is configured in Sodia/settings.py

urlpatterns = [
    path("", include("users.urls")),  # paths from app users
    path("settings/", include("settings.urls")),  # paths from app settings
    path("message/", include("messaging.urls")),  # paths from app messaging
    path("api/", include("api.urls")),  # paths from app api for API endpoints
]
