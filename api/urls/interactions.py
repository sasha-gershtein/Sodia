from django.urls import path

from interactions import api

app_name = 'interactions'

urlpatterns = [
    path('friend/send/', api.send_friend_request, name='send_friend_request'),
    path('friend/respond/', api.respond_to_friend_request, name='respond_to_friend_request'),
    path('friend/withdraw/', api.withdraw_friend_request, name='withdraw_friend_request'),
]
