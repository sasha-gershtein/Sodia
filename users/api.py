from api.decorators import api_view, api_login_required
from api.errors import parse_form_errors, BadRequestError, NotFoundError
from django.urls import reverse

from settings.models import UserAccountSettings

from .forms import LoginForm, RegistrationForm, ChangePasswordForm
from .middleware import SessionData
from .models import User


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
            "location": reverse("users:home")  # TODO: registration
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


@api_login_required
def partial_user_info(_request, _user, data):
    try:
        if data.get("id") is not None:
            requested_user = User.objects.activated().get(pk=data["id"])
        elif data.get("username") is not None:
            requested_user = UserAccountSettings.objects.activated().get(username=data["username"]).user
        else:
            raise BadRequestError("User must be identified via id or username")
    except (User.DoesNotExist, UserAccountSettings.DoesNotExist):
        raise NotFoundError("User does not exist")
    return {
        "id": requested_user.id,
        "username": requested_user.account_settings.username,
        "first_name": requested_user.account_settings.first_name,
        "last_name": requested_user.account_settings.last_name,
        "display_name": requested_user.account_settings.get_display_name(),
    }
