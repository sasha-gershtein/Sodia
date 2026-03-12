from django.urls import reverse

from .forms import LoginForm, RegistrationForm, ChangePasswordForm, SearchForm
from .middleware import SessionData
from .models import User

from api.decorators import api_view, api_login_required
from api.errors import parse_form_errors


@api_view
def login(request, data):
    form = LoginForm(data)
    if not form.is_valid():
        raise parse_form_errors(form)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(form.cleaned_data["user"])
    return {
        "redirect": {
            "location": reverse("users:home")  # TODO: random dialogue
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


@api_login_required
def get_own_info(_request, user: User, _data):
    return user.info(user).partial


@api_login_required
def partial_user_info(_request, user: User, data):
    return User.objects.get_user_by_data(data).info(user).partial  # validates and raises appropriate exceptions


@api_login_required
def full_user_info(_request, user: User, data):
    return User.objects.get_user_by_data(data).info(user).full  # validates and raises appropriate exceptions


@api_login_required
def search(_request, user: User, data):
    form = SearchForm(data)
    if not form.is_valid():
        raise parse_form_errors(form)
    query = form.cleaned_data.get("query", "")
    return [
        result.partial
        for result in user.search(query)
    ]


def get_sodia_button_info(user: User):
    query_set = User.objects.pressing_sodia_button().exclude(pk=user.pk)
    if user.is_pressing_sodia_button:
        sodia_button_info = [
            user_pressing_button.info(user).partial
            for user_pressing_button in query_set
        ]
    else:
        sodia_button_info = query_set.count()
    return {
        "is_pressing_sodia_button": user.is_pressing_sodia_button,
        "sodia_button_info": sodia_button_info,
    }


@api_login_required
def load_home(_request, user: User, _data):
    return get_sodia_button_info(user)


@api_login_required
def press_sodia_button(_request, user: User, _data):
    user.press_sodia_button()
    return get_sodia_button_info(user)

@api_login_required
def unpress_sodia_button(_request, user: User, _data):
    user.unpress_sodia_button()
    return get_sodia_button_info(user)
