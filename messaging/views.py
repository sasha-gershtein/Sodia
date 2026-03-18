"""This file defines views of app "messaging\""""

from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse

from users.decorators import login_required
from users.models import User


class Dialogue404(Http404):
    """A subclass of Http404 error
    to be used by 404-handler to distinguish dialogue-not-found errors from page-not-found errors"""
    pass


@login_required
def message_user(request, user: User, username: str):
    """messaging page view (with selected dialogue)"""
    # check that requested dialogue's user exists
    if (interlocutor := User.objects.get_user_by_username(username)) is None:
        raise Dialogue404()
    if user == interlocutor:
        # cannot message yourself, just redirect to messaging home page
        # this is a valid url for every other user, so no 404 error
        return redirect(reverse("messaging:message-home"))
    return render(request, "messaging/message.html")


@login_required
def message_home(request, _user: User):
    """messaging page view (without selected dialogue)"""
    return render(request, "messaging/message.html")
