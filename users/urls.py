"""This file defines paths of app "users" that are accessible on the website, except for static files."""

from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    # home view (authorised home page and unauthorised login/signup page)
    path("", views.Home.as_view(), name="home"),
    path("profile/<str:username>/", views.profile, name="profile"),  # user profile page
    path("search/", views.search, name="search"),  # user search page
]
