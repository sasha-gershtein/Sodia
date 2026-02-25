from django.urls import reverse

from .forms import LoginForm, RegistrationForm, ChangePasswordForm
from .middleware import SessionData
from .models import User

from api.decorators import api_view, api_login_required
from api.errors import parse_form_errors
from interactions.models import UserInfo


@api_view
def login(request, data):
    form = LoginForm(data)
    if not form.is_valid():
        raise parse_form_errors(form)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(form.cleaned_data["user"])
    return {
        "redirect": {
            "location": reverse("users:home")
        }
    }


@api_view
def logout(request, _data):
    session_data: SessionData = request.session_data
    session_data.session.logout()
    session_data.reset_cookies = True
    return {
        "redirect": {
            "location": reverse("users:home")
        }
    }


@api_view
def register(request, data):
    form = RegistrationForm(data)
    if not form.is_valid():
        raise parse_form_errors(form)
    user = User.objects.create_user(**form.cleaned_data)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(user)
    return {
        "redirect": {
            "location": reverse("settings:account")  # TODO: registration
        }
    }


@api_login_required
def change_password(request, user: User, data):
    form = ChangePasswordForm(data, user=user)
    if not form.is_valid():
        raise parse_form_errors(form)
    user.login_details.password = form.cleaned_data["new_password"]
    user.login_details.save()
    session_data: SessionData = request.session_data
    session_data.session.authenticate(user)


def get_user_info(requesting_user, data, keys):
    user_data = UserInfo(
        User.objects.get_user_by_data(data),  # validates and raises appropriate exceptions
        requesting_user
    )
    return {
        key: value.get_json_value() if hasattr(value, "get_json_value") else value
        for key in keys
        if (value := getattr(user_data, key)) is not None
    }


PARTIAL = {
    "id",
    "username",
    "first_name",
    "last_name",
    "display_name",
    "relation",
    "can_message",
}


@api_login_required
def partial_user_info(_request, user, data):
    return get_user_info(user, data, PARTIAL)


FULL = {
    "id",
    "username",
    "first_name",
    "last_name",
    "display_name",
    "gender",
    "birth_date",
    "description",
    "challenge_streak",
    "year_group",
    "house",
    "boarding_type",
    "country",
    "relation",
    "can_message",
}


@api_login_required
def full_user_info(_request, user, data):
    return get_user_info(user, data, FULL)