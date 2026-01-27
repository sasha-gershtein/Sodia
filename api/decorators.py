from functools import wraps
import json

from django.views.decorators.http import require_http_methods
from django.http import HttpRequest, JsonResponse

from Sodia.settings import DEBUG

from .errors import ApiError, InternalServerError, InvalidJsonError, ErrorResponse

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
            data = json.loads(body) if body else None
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

# TODO: login_required_api_view