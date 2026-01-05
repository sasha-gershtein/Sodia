from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views import View

from .middleware import SessionData
from .decorators import login_required
from .models import User

class Home(View):
    def dispatch(self, request, *args, **kwargs):
        session_data: SessionData = request.session_data
        if session_data.user is None:
            return self.unauthorised(request)
        return self.home(request)

    # noinspection PyMethodMayBeStatic
    def unauthorised(self, request):
        return render(request, 'users/unauthorised.html')

    @method_decorator(login_required)
    # noinspection PyMethodMayBeStatic
    def home(self, request, user: User):
        return render(request, 'users/home.html', {'user': user})
