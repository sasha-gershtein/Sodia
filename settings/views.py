from django.shortcuts import render

import users.models
from users.decorators import login_required


@login_required
def index(request, _user: users.models.User):
    return render(request, 'settings/index.html')


@login_required
def account(request, _user: users.models.User):
    return render(request, 'settings/account.html')


@login_required
def privacy(request, _user: users.models.User):
    return render(request, 'settings/privacy.html')


@login_required
def notifications(request, _user: users.models.User):
    return render(request, 'settings/notifications.html')


@login_required
def challenges(request, _user: users.models.User):
    return render(request, 'settings/challenges.html')