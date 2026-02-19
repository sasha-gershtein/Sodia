from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views import View
from django.http import Http404

from .middleware import SessionData
from .decorators import login_required
from .models import User
from .forms import LoginForm, RegistrationForm


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
        context = {
            "user": user,
        }
        return render(request, 'users/home.html', context)

@login_required
def profile(request, _user, username: str, *args, **kwargs):
    if User.objects.get_user_by_username(username) is None:
        raise Http404
    return render(request, 'users/profile.html')
