from django.urls import path

from users import api

app_name = 'users'

urlpatterns = [
    path('login', api.login, name='login'),
    path('logout', api.logout, name='logout'),
    path('register', api.register, name='register'),
    path('change-password', api.change_password, name='change_password'),
]
