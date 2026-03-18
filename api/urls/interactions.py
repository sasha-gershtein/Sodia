"""This file defines paths of API endpoints for app "interactions\""""

from django.urls import path

from interactions import api

app_name = "interactions"

urlpatterns = [
    path("friend/send/", api.send_friend_request, name="send_friend_request"),
    path("friend/respond/", api.respond_to_friend_request, name="respond_to_friend_request"),
    path("friend/withdraw/", api.withdraw_friend_request, name="withdraw_friend_request"),
    path("friend/remove/", api.remove_friend, name="remove_friend"),
    path("get-friends/", api.get_friends, name="get_friends"),
    path("block/", api.block, name="block"),
    path("unblock/", api.unblock, name="unblock"),
]
