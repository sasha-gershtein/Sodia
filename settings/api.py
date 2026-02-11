from api.decorators import api_login_required
from api.errors import parse_form_errors

from .forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm


def update_model(form):
    if not form.is_valid():
        raise parse_form_errors(form)
    form.save()
    return {
        key: value.get_json_value() if hasattr(value, "get_json_value") else value
        for key, value in form.cleaned_data.items()
    }


@api_login_required
def account(_request, user, data):
    return update_model(AccountForm.get_updated_form(data, instance=user.account_settings))


@api_login_required
def privacy(_request, user, data):
    return update_model(PrivacyForm.get_updated_form(data, instance=user.privacy_settings))


@api_login_required
def notifications(_request, user, data):
    return update_model(NotificationsForm.get_updated_form(data, instance=user.notifications_settings))


@api_login_required
def challenges(_request, user, data):
    return update_model(ChallengesForm.get_updated_form(data, instance=user.challenges_settings))
