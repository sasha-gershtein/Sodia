from api.decorators import api_view
from api.errors import UnauthorizedError

from .forms import LoginForm

from .middleware import SessionData


@api_view
def login(request, data):
    form = LoginForm(data)
    if not form.is_valid():
        raise UnauthorizedError("Invalid username/email or password.", reason="INVALID_CREDENTIALS")
    session_data: SessionData = request.session_data
    session_data.session.authenticate(form.user)
