from django.http import Http404
from django.shortcuts import render, redirect
from django.urls import reverse

from users.decorators import login_required
from users.models import User


@login_required
def message_user(request, user: User, username: str):
    if (interlocutor := User.objects.get_user_by_username(username)) is None:
        raise Http404
    if user == interlocutor:
        return redirect(reverse("messaging:message-home"))
    return render(request, 'messaging/message.html')


@login_required
def message_home(request, _user: User):
    return render(request, 'messaging/message.html')
