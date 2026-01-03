from django.urls import path
from . import views

urlpatterns = [
    path('', views.Home.as_view(), name='home'),
    path('auth', views.Auth.as_view(), name='auth'),  # temp debug view
]