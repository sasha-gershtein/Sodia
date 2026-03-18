"""this file defines the login_required decorator
to be used in views that should only be accessible by authenticated users"""

from functools import wraps

from django.shortcuts import redirect
from django.http import HttpRequest
from django.urls import reverse

from .middleware import SessionData


def login_required(func):
    """use this decorator on a view function to make the view require authentication
    if a request is not authenticated, user is redirected to login page (home page)
    otherwise, the view function is called with signature (request, user: User, *args, **kwargs)"""

    @wraps(func)  # keep the original function's metadata
    def wrapper(request: HttpRequest, *args, **kwargs):
        session_data: SessionData | None = getattr(request, "session_data", None)
        if session_data is None or session_data.user is None:
            return redirect(reverse("users:home"))  # redirect to the home page if session is not authenticated

        return func(request, session_data.user, *args, **kwargs)  # call the original view if session is authenticated

    return wrapper  # return the decorated view function
