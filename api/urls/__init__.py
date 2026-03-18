"""This file references lists with paths of API endpoints of all other project apps"""

from django.urls import path, include

from api.views import api_root_404

app_name = "api"

urlpatterns = [
    path("", api_root_404, name="root"),  # root raising Http404()
    path("users/", include("api.urls.users", namespace="users")),
    path("settings/", include("api.urls.settings", namespace="settings")),
    path("interactions/", include("api.urls.interactions", namespace="interactions")),
    path("messaging/", include("api.urls.messaging", namespace="messaging")),
    path("updates/", include("api.urls.updates", namespace="updates")),
]
