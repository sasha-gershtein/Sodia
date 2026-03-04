from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.message_home, name='message-home'),
    path('<str:username>/', views.message_user, name='message-user'),
]