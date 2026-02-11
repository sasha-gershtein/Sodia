from django.urls import path
from . import views

app_name = 'settings'

urlpatterns = [
    path('', views.index, name='index'),
    path('account', views.account, name='account'),
    path('privacy', views.privacy, name='privacy'),
    path('notifications', views.notifications, name='notifications'),
    path('challenges', views.challenges, name='challenges'),
]