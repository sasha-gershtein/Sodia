from django.urls import path

from settings import api

app_name = 'settings'

urlpatterns = [
    path('account/save', api.Account.save, name='account.save'),
    path('privacy/save', api.Privacy.save, name='privacy.save'),
    path('notifications/save', api.Notifications.save, name='notifications.save'),
    path('challenges/save', api.Challenges.save, name='challenges.save'),
]
