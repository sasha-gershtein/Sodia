"""This file defines decorators for API views to parse data and handle errors"""

from functools import wraps
import json

from django.http import HttpRequest, JsonResponse

from Sodia.settings import DEBUG
from Sodia.views import handle405

from users.middleware import SessionData

from .errors import ApiError, InternalServerError, InvalidJsonError, ErrorResponse, UnauthorizedError

# POST is the only allowed method for API, but GET is enabled for debugging
METHODS = ["POST", "GET"] if DEBUG else ["POST"]


def process_api_errors(func):
    """decorate a view function to handle any exceptions it raises and return valid JSON response"""

    @wraps(func)  # keep the original function's metadata
    def wrapper(request, *args, **kwargs):
        # noinspection PyBroadException
        try:
            return func(request, *args, **kwargs)
        except ApiError as e:
            # if an ApiError is raised, return its details
            return ErrorResponse(e)
        except Exception:
            # A view raised an unexpected exception
            if DEBUG:
                # raise the exception for Django to display its details at debug
                raise
            # return a JSON 500 error response
            return ErrorResponse(InternalServerError())

    return wrapper


def api_view(func):
    """decorate an API view functions to parse data, return data in standard format, and handle exceptions.
    The original view is called with the signature (request, data, *args, **kwargs)"""

    @process_api_errors  # handle exceptions
    @wraps(func)  # keep the original function's metadata
    def wrapper(request: HttpRequest, *args, **kwargs):
        if request.method not in METHODS:
            # if method not allowed, return an error (non-json)
            return handle405(request, METHODS)
        body = request.body.decode("utf-8")
        try:
            data = json.loads(body) if body else {}  # parse json or set default to {} if body is missing
        except json.decoder.JSONDecodeError:
            raise InvalidJsonError()
        response = func(request, data, *args, **kwargs)  # call the view
        return JsonResponse(  # return JSON response in standard format
            data={
                "success": True,
                "result": response if response is not None else {},
                "error": None,
            }
        )

    return wrapper


def api_login_required(func):
    """decorate an API view function to require authentication and everything from @api_view.
    The original view is called with the signature (request, user: User, data, *args, **kwargs)"""

    @api_view
    @wraps(func)  # keep the original function's metadata
    def wrapper(request: HttpRequest, data, *args, **kwargs):
        session_data: SessionData | None = getattr(request, "session_data", None)
        if session_data is None or session_data.user is None:
            # user is not authorised, return error response and redirect to login
            raise UnauthorizedError(f"{request.path} requires authentication")

        return func(request, session_data.user, data, *args, **kwargs)  # call the view

    return wrapper
