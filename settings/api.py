"""This file defines API views that handle API requests to get or update user's settings"""

from api.decorators import api_login_required
from api.errors import parse_form_errors

from .forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm


def update_model(form):
    """function to update db row from ModelForm if form is valid, and return current values"""
    if not form.is_valid():
        # return an error response
        raise parse_form_errors(form)
    form.save()  # save to db
    return {  # return updated values
        key: value.get_json_value() if hasattr(value, "get_json_value") else value
        for key, value in form.cleaned_data.items()
    }


@api_login_required
def account(_request, user, data):
    """get or update account settings API view"""
    return update_model(AccountForm.get_updated_form(data, instance=user.account_settings))


@api_login_required
def privacy(_request, user, data):
    """get or update privacy settings API view"""
    return update_model(PrivacyForm.get_updated_form(data, instance=user.privacy_settings))


@api_login_required
def notifications(_request, user, data):
    """get or update notifications settings API view"""
    return update_model(NotificationsForm.get_updated_form(data, instance=user.notifications_settings))


@api_login_required
def challenges(_request, user, data):
    """get or update challenges settings API view"""
    return update_model(ChallengesForm.get_updated_form(data, instance=user.challenges_settings))
