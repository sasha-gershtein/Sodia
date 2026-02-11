from django.urls import path

from settings import api

app_name = 'settings'

urlpatterns = [
    path('account/', api.account, name='account'),
    path('privacy/', api.privacy, name='privacy'),
    path('notifications/', api.notifications, name='notifications'),
    path('challenges/', api.challenges, name='challenges'),
]
