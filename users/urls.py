from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('profile/<str:username>/', views.profile, name='profile'),
]