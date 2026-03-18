"""This file defines paths of API endpoints for app "updates\""""

from django.urls import path

from updates import api

app_name = "updates"

urlpatterns = [
    path("", api.get_updates, name="get_updates"),
]
