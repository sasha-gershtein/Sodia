"""This file defines views of app "users\""""

from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views import View
from django.http import Http404

from .middleware import SessionData
from .decorators import login_required
from .models import User
from .forms import LoginForm, RegistrationForm, SearchForm


class Home(View):
    """Class-based home page view for two possible versions:
    * "unauthorised" login page is displayed for unauthorised users
    * "authorised" home page is displayed for authorised users"""

    def dispatch(self, request, *args, **kwargs):
        """determine which view to call based on request"""
        session_data: SessionData = request.session_data
        if session_data.user is None:
            return self.unauthorised(request)
        return self.home(request)

    # noinspection PyMethodMayBeStatic
    def unauthorised(self, request):
        context = {  # create forms for rendering
            "login_form": LoginForm(),
            "registration_form": RegistrationForm(),
        }
        return render(request, "users/unauthorised.html", context)

    @method_decorator(login_required)
    # noinspection PyMethodMayBeStatic
    def home(self, request, _user: User):
        return render(request, "users/home.html")


class Profile404(Http404):
    """A subclass of Http404 error
    to be used by 404-handler to distinguish profile-not-found errors from page-not-found errors"""
    pass


@login_required
def profile(request, _user: User, username: str):
    """profile page view"""
    # check that requested user exists
    if User.objects.get_user_by_username(username) is None:
        raise Profile404()
    return render(request, "users/profile.html")


@login_required
def search(request, _user: User):
    """search page view"""
    context = {
        "search_form": SearchForm(),  # create a search form for rendering
    }
    return render(request, "users/search.html", context)
