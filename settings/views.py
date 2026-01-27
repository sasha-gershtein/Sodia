from django.shortcuts import render

import users.models
from settings.forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm
from users.decorators import login_required
from users.forms import ChangePasswordForm


@login_required
def index(request, _user: users.models.User):
    return render(request, 'settings/index.html')


@login_required
def account(request, _user: users.models.User):
    context = {  # TODO: password change form
        "change_password_form": ChangePasswordForm(),
        "account_form": AccountForm(),
    }
    return render(request, 'settings/account.html', context)


@login_required
def privacy(request, _user: users.models.User):
    context = {
        "privacy_form": PrivacyForm(),
    }
    return render(request, 'settings/privacy.html', context)


@login_required
def notifications(request, _user: users.models.User):
    context = {
        "notifications_form": NotificationsForm(),
    }
    return render(request, 'settings/notifications.html', context)


@login_required
def challenges(request, _user: users.models.User):
    context = {
        "challenges_form": ChallengesForm(),
    }
    return render(request, 'settings/challenges.html', context)