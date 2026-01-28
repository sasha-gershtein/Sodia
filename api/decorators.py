from functools import wraps
import json

from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, JsonResponse

from Sodia.settings import DEBUG

from users.middleware import SessionData

from .errors import ApiError, InternalServerError, InvalidJsonError, ErrorResponse, UnauthorizedError

METHODS = ["POST", "GET"] if DEBUG else ["POST"]


def process_api_errors(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        # noinspection PyBroadException
        try:
            return func(request, *args, **kwargs)
        except ApiError as e:
            return ErrorResponse(e)
        except Exception:
            if DEBUG:
                raise
            return ErrorResponse(InternalServerError())

    return wrapper


def api_view(func):
    @require_http_methods(METHODS)
    @process_api_errors
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        body = request.body.decode("utf-8")
        try:
            data = json.loads(body) if body else {}
        except json.decoder.JSONDecodeError:
            raise InvalidJsonError
        response = func(request, data, *args, **kwargs)
        return JsonResponse(
            data={
                "success": True,
                "result": response,
                "error": None,
            }
        )

    return wrapper


def api_login_required(func):
    @api_view
    @wraps(func)
    def wrapper(request: HttpRequest, data, *args, **kwargs):
        session_data: SessionData | None = getattr(request, "session_data", None)
        if session_data is None or session_data.user is None:
            raise UnauthorizedError(f"{request.path} requires authentication")

        return func(request, session_data.user, data, *args, **kwargs)

    return wrapper
