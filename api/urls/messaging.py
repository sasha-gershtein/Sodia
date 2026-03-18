"""This file defines paths of API endpoints for app "messaging\""""

from django.urls import path

from messaging import api

app_name = "messaging"

urlpatterns = [
    path("get-dialogues/", api.get_dialogues, name="get_dialogues"),
    path("load-dialogue/", api.get_dialogue_messages, name="get-dialogue-messages"),
    path("mark-read/", api.mark_read, name="mark-read"),
    path("send-message/", api.send_message, name="send-message"),
]
