from functools import wraps

from django.shortcuts import redirect

from .middleware import SessionData


def login_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        session_data: SessionData | None = getattr(request, "session_data", None)
        if session_data is None or session_data.user is None:
            return redirect("/")

        return func(request, session_data.user, *args, **kwargs)

    return wrapper
