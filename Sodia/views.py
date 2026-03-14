from django.shortcuts import render
from django.urls import reverse

from api.errors import NotFoundError, ErrorResponse
from messaging.views import Dialogue404
from users.middleware import SessionData
from users.views import Profile404


def handle404(request, exception):
    if request.path.startswith(reverse('api:root')):
        from api.decorators import METHODS

        if request.method not in METHODS:
            return handle405(request, METHODS)
        return ErrorResponse(NotFoundError("Api method not found"))
    if isinstance(exception, Profile404):
        return render(request, "errors/404-profile.html", status=404)
    if isinstance(exception, Dialogue404):
        return render(request, "errors/404-dialogue.html", status=404)
    context = {
        "error": "errors/404.html",
        "title": "Not found",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:
        return render(request, "errors/auth_error.html", context=context, status=404)
    return render(request, "errors/unauth_error.html", context=context, status=404)


# noinspection PyUnusedLocal
def csrf_failure(request, reason):
    context = {
        "error": "errors/403-csrf.html",
        "title": "Something went wrong",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:
        return render(request, "errors/auth_error.html", context=context, status=403)
    return render(request, "errors/unauth_error.html", context=context, status=403)


def handle405(request, allow=("POST",)):
    context = {
        "error": "errors/405-api.html",
        "title": "Method not allowed",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:
        response = render(request, "errors/auth_error.html", context=context, status=405)
    else:
        response = render(request, "errors/unauth_error.html", context=context, status=405)
    response["Allow"] = ", ".join(allow)
    return response


def handle500(request):
    context = {
        "error": "errors/500.html",
        "title": "Something went wrong",
    }
    session_data: SessionData = getattr(request, "session_data", None)
    if session_data and session_data.user:
        return render(request, "errors/auth_error.html", context=context, status=500)
    return render(request, "errors/unauth_error.html", context=context, status=500)
