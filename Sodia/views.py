"""
This file defines global views for error pages: 404, 403, 405, and 500.
These views determine whether a "logged-in" page version is shown or not
- the normal navigation header is on the "logged-in" pages.
"""

from django.shortcuts import render
from django.urls import reverse

from api.errors import NotFoundError, ErrorResponse
from messaging.views import Dialogue404
from users.middleware import SessionData
from users.views import Profile404


def handle404(request, exception):
    """Handle 404 (Not Found) errors."""
    if request.path.startswith(reverse("api:root")):
        # if the request is for an API endpoint, show a json-formatted error instead
        from api.decorators import METHODS

        if request.method not in METHODS:
            # if DEBUG=False, only POST requests are permitted for /api/
            # if the request method is different, even if the API endpoint isn't found, show a 405 error
            return handle405(request, METHODS)
        return ErrorResponse(NotFoundError("Api method not found"))  # return a json not found error

    if isinstance(exception, Profile404):
        # if the request is for a user profile which doesn't exist, show a special profile-not-found error page
        return render(request, "errors/404-profile.html", status=404)
    if isinstance(exception, Dialogue404):
        # if the request is for a dialogue which doesn't exist, show a special dialogue-not-found error page
        return render(request, "errors/404-dialogue.html", status=404)
    context = {
        "error": "errors/404.html",
        "title": "Not found",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:  # if session is authorised, show a "logged-in" version
        return render(request, "errors/auth_error.html", context=context, status=404)
    return render(request, "errors/unauth_error.html", context=context, status=404)


# noinspection PyUnusedLocal
def csrf_failure(request, reason):
    """Handle 404 (Forbidden) errors when CSRF protection fails.
    This is likely to happen if an html form submission is handled by the browser, and not JavaScript."""
    context = {
        "error": "errors/403-csrf.html",
        "title": "Something went wrong",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:  # if session is authorised, show a "logged-in" version
        return render(request, "errors/auth_error.html", context=context, status=403)
    return render(request, "errors/unauth_error.html", context=context, status=403)


def handle405(request, allow=("POST",)):
    """Handle 405 (Method Not Allowed) errors.
    This is likely to happen if a user is navigated to an /api/ page using a GET request."""
    context = {
        "error": "errors/405-api.html",
        "title": "Method not allowed",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:  # if session is authorised, show a "logged-in" version
        response = render(request, "errors/auth_error.html", context=context, status=405)
    else:
        response = render(request, "errors/unauth_error.html", context=context, status=405)
    response["Allow"] = ", ".join(allow)  # add a header specifying which HTTP methods are allowed
    return response


def handle500(request):
    """Handle 500 (Internal Server Error) errors.
    This page should not ideally ever be displayed on the website, all exceptions are to be handled
    by the applications that may raise them. This page is important for the purposes of defensive programming, because
    there is always a non-zero chance of an overlooked bug.
    Due to this view, it is impossible to actually crash the server, unless there is a bug in this subroutine."""
    context = {
        "error": "errors/500.html",
        "title": "Something went wrong",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:  # if session is authorised, show a "logged-in" version
        return render(request, "errors/auth_error.html", context=context, status=500)
    return render(request, "errors/unauth_error.html", context=context, status=500)
