import math

from django.core.exceptions import ValidationError
from django.forms import forms
from django.http import JsonResponse


class ApiError(Exception):
    code: int = 500
    reason: str = "GENERIC"
    message: str = "Internal Server Error"

    def __init__(self, message=None, *args, code=None, reason=None, meta=None):
        super().__init__(*args)
        self.code = code if code is not None else self.code
        self.reason = reason if reason is not None else self.reason
        self.message = message if message is not None else self.message
        self.meta = meta


class InternalServerError(ApiError):
    reason = "INTERNAL_SERVER_ERROR"


class ClientError(ApiError, ValueError):
    code = 400
    reason = "CLIENT_GENERIC"
    message = "Client Error"


class BadRequestError(ClientError):
    code = 400
    reason = "BAD_REQUEST"
    message = "Bad Request"


class InvalidJsonError(BadRequestError):
    reason = "INVALID_JSON"
    message = "Invalid JSON"


class UnauthorizedError(ClientError):
    code = 401
    reason = "UNAUTHORIZED"
    message = "Unauthorized"


class ForbiddenError(ClientError):
    code = 403
    reason = "FORBIDDEN"
    message = "Forbidden"


class NotFoundError(ClientError):
    code = 404
    reason = "NOT_FOUND"
    message = "Not Found"


class ConflictError(ClientError):
    code = 409
    reason = "CONFLICT"
    message = "Conflict"


class TooManyRequestsError(ClientError):
    code = 429
    reason = "TOO_MANY_REQUESTS"
    message = "Too Many Requests"


class BadUserInputError(ClientError):
    code = 499
    reason = "BAD_USER_INPUT"
    message = "Bad input. Please check and try again"


class APIValidationError(BadUserInputError):
    reason = "VALIDATION"
    message = "Validation error. Please check your input and try again"


class FormResponseUserError(ValidationError):
    """Subclass of django.core.exceptions.ValidationError.
    Used for semantic validation errors, i.e. validation that can only be completed by the server, not the client.
    These errors might be treated differently by the client than simple ValidationErrors."""

    def __init__(self, *args, priority: int | float = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.priority = priority


def parse_form_errors(form: forms.BaseForm):
    assert form.errors, "parse_form_errors should only be called on invalid forms"
    user_error = FormResponseUserError(message="", priority=-math.inf)
    for field_errors in form.errors.as_data().values():
        for error in field_errors:
            if not isinstance(error, FormResponseUserError):
                return APIValidationError(meta=form.errors)

            if error.priority > user_error.priority:
                user_error = error

    # TODO: change forms.js to reflect new protocol
    return BadUserInputError(meta=form.errors, reason=user_error.code.upper() if user_error.code else None)


def ErrorResponse(e: ApiError):
    return JsonResponse(
        data={
            "success": False,
            "result": None,
            "error": {
                "code": e.code,
                "reason": e.reason,
                "message": e.message,
                "meta": e.meta
            },
        },
        status=e.code,
        reason=e.reason.replace("_", " ").title(),
    )
