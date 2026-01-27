from api.decorators import api_view
from api.errors import parse_form_errors

from .forms import AccountForm, PrivacyForm, NotificationsForm, ChallengesForm


class Account:
    @staticmethod
    @api_view
    def save(_request, data):
        form = AccountForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Privacy:
    @staticmethod
    @api_view
    def save(_request, data):
        form = PrivacyForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Notifications:
    @staticmethod
    @api_view
    def save(_request, data):
        form = NotificationsForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }


class Challenges:
    @staticmethod
    @api_view
    def save(_request, data):
        form = ChallengesForm(data)
        if not form.is_valid():
            raise parse_form_errors(form)
        return {
            "message": "received"
        }
