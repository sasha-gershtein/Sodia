from api.decorators import api_view
from api.errors import UserInputError, ValidationError as APIValidationError
from django.urls import reverse

from .forms import LoginForm

from .middleware import SessionData


@api_view
def login(request, data):
    form = LoginForm(data)
    if not form.is_valid():
        non_field = form.non_field_errors().as_data()
        if len(non_field) and non_field[0].code == "invalid_credentials":
            raise UserInputError("Invalid username/email or password.", reason="INVALID_CREDENTIALS")
        raise APIValidationError(meta=form.errors)
    session_data: SessionData = request.session_data
    session_data.session.authenticate(form.cleaned_data["user"])
    return {
        "redirect": {
            "location": reverse("users:home")
        }
    }
