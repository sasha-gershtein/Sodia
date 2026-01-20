from api.decorators import api_view
from api.errors import parse_form_errors
from django.urls import reverse

from .forms import LoginForm, RegistrationForm

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
def logout(request, data):
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
            "location": reverse("users:home")
        }
    }