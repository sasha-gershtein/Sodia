from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views import View
from django.http import Http404

from .middleware import SessionData
from .decorators import login_required
from .models import User
from .forms import LoginForm, RegistrationForm, SearchForm


class Home(View):
    def dispatch(self, request, *args, **kwargs):
        session_data: SessionData = request.session_data
        if session_data.user is None:
            return self.unauthorised(request)
        return self.home(request)

    # noinspection PyMethodMayBeStatic
    def unauthorised(self, request):
        context = {
            "login_form": LoginForm(),
            "registration_form": RegistrationForm(),
        }
        return render(request, 'users/unauthorised.html', context)

    @method_decorator(login_required)
    # noinspection PyMethodMayBeStatic
    def home(self, request, user: User):
        return render(request, 'users/home.html')


class Profile404(Http404):
    pass


@login_required
def profile(request, _user: User, username: str):
    if User.objects.get_user_by_username(username) is None:
        raise Profile404()
    return render(request, 'users/profile.html')


@login_required
def search(request, _user: User):
    context = {
        "search_form": SearchForm()
    }
    return render(request, 'users/search.html', context)