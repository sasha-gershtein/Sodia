from django.urls import path
import users.api

urlpatterns = [
    path('login', users.api.login, name='login'),
]