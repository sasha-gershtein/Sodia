"""This file defines API views that handle API requests related to the "users" app and its models"""

from django.urls import reverse

from .forms import LoginForm, RegistrationForm, ChangePasswordForm, SearchForm
from .middleware import SessionData
from .models import User

from api.decorators import api_view, api_login_required
from api.errors import parse_form_errors


@api_view
def login(request, data):
    """verify password and authenticate user (attach to a session)"""
    form = LoginForm(data)
    if not form.is_valid():  # validate email/username and password
        # if failed, return an error response
        raise parse_form_errors(form)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(form.cleaned_data["user"])  # attach user to the session
    return {
        "redirect": {
            "location": reverse("users:home"),  # redirect user to the home page
        }
    }


@api_view
def logout(request, _data):
    """logout user, reset session"""
    session_data: SessionData = request.session_data
    session_data.session.logout()  # reset session
    session_data.reset_cookies = True  # signal to middleware to reset client cookies
    return {
        "redirect": {
            "location": reverse("users:home"),  # redirect user to the home page
        }
    }


@api_view
def register(request, data):
    """create a new user account"""
    form = RegistrationForm(data)
    if not form.is_valid():
        # form is not filled in correctly or a user with this email address already exists
        raise parse_form_errors(form)
    user = User.objects.create_user(**form.cleaned_data)  # create user and associated settings rows
    session_data: SessionData = request.session_data
    session_data.session.authenticate(user)  # attach user to the session
    return {
        "redirect": {
            "location": reverse("settings:account")  # TODO: registration
        }
    }


@api_login_required
def change_password(request, user: User, data):
    """change password of a user"""
    form = ChangePasswordForm(data, user=user)
    if not form.is_valid():  # verify old login details
        # if validation is failed, return an error response
        raise parse_form_errors(form)
    # store new password (automatically hashed by PasswordField)
    user.login_details.password = form.cleaned_data["new_password"]
    user.login_details.save()
    # all user sessions are automatically invalidated on password change by design
    # so reauthenticate this specific session for the user (all other sessions are logged out)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(user)


@api_login_required
def get_own_info(_request, user: User, _data):
    """fetch info of the authenticated user"""
    return user.info(user).partial


@api_login_required
def partial_user_info(_request, user: User, data):
    """fetch partial info of another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    return User.objects.get_user_by_data(data).info(user).partial


@api_login_required
def full_user_info(_request, user: User, data):
    """fetch full info of another user"""
    # get_user_by_data() validates data and raises exceptions if invalid
    # (hence this view returns an appropriate error response)
    return User.objects.get_user_by_data(data).info(user).full


@api_login_required
def search(_request, user: User, data):
    """search activated users"""
    form = SearchForm(data)  # validates maximum length of the query
    if not form.is_valid():
        raise parse_form_errors(form)
    query = form.cleaned_data.get("query", "")
    return [
        result.partial  # return partial info of a found user
        for result in user.search(query)  # for every user in search results
    ]


def get_sodia_button_info(user: User):
    """return info of the current sodia button state for a given user
    and the [list if pressing, count otherwise] of other people pressing it.
    This function is not a view, bit it is used in views below"""
    query_set = User.objects.pressing_sodia_button().exclude(pk=user.pk)  # query set of other users pressing the button
    if user.is_pressing_sodia_button:
        sodia_button_info = [  # return a list of partial info of all other users pressing the button
            user_pressing_button.info(user).partial
            for user_pressing_button in query_set
        ]
    else:
        sodia_button_info = query_set.count()  # if user is not pressing, only return the count
    return {
        "is_pressing_sodia_button": user.is_pressing_sodia_button,
        "sodia_button_info": sodia_button_info,
    }


@api_login_required
def load_home(_request, user: User, _data):
    """load home page status (Sodia Button state)"""
    return get_sodia_button_info(user)


@api_login_required
def press_sodia_button(_request, user: User, _data):
    """press Sodia Button and return the updated Button info"""
    user.press_sodia_button()
    return get_sodia_button_info(user)


@api_login_required
def unpress_sodia_button(_request, user: User, _data):
    """unpress (stop pressing) Sodia Button and return the updated Button info"""
    user.unpress_sodia_button()
    return get_sodia_button_info(user)
