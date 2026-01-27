from api.decorators import api_login_required
from api.errors import parse_form_errors

from .forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm


class Account:
    @staticmethod
    @api_login_required
    def save(_request, _user, data):
        form = AccountForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Privacy:
    @staticmethod
    @api_login_required
    def save(_request, _user, data):
        form = PrivacyForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Notifications:
    @staticmethod
    @api_login_required
    def save(_request, _user, data):
        form = NotificationsForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Challenges:
    @staticmethod
    @api_login_required
    def save(_request, _user, data):
        form = ChallengesForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }
