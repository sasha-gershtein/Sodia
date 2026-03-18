"""This file defines views of app "settings\""""

from django.shortcuts import render

import users.models
from settings.forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm
from users.decorators import login_required
from users.forms import ChangePasswordForm


@login_required
def index(request, _user: users.models.User):
    """index of settings page with links to individual settings pages"""
    return render(request, "settings/index.html")


@login_required
def account(request, _user: users.models.User):
    """account settings page view"""
    context = {  # create forms for rendering
        "change_password_form": ChangePasswordForm(),
        "account_form": AccountForm(),
    }
    return render(request, "settings/account.html", context)


@login_required
def privacy(request, _user: users.models.User):
    """privacy settings page view"""
    context = {
        "privacy_form": PrivacyForm(),  # create form for rendering
    }
    return render(request, "settings/privacy.html", context)


@login_required
def notifications(request, _user: users.models.User):
    """notifications settings page view"""
    context = {
        "notifications_form": NotificationsForm(),  # create form for rendering
    }
    return render(request, "settings/notifications.html", context)


@login_required
def challenges(request, _user: users.models.User):
    """challenges settings page view"""
    context = {
        "challenges_form": ChallengesForm(),  # create form for rendering
    }
    return render(request, "settings/challenges.html", context)
