from django.http import JsonResponse


class ApiError(Exception):
    code: int = 500
    reason: str = "GENERIC"
    message: str = "Internal Server Error"

    def __init__(self, message=None, *args, code=None, reason=None):
        super().__init__(*args)
        self.code = code if code is not None else self.code
        self.reason = reason if reason is not None else self.reason
        self.message = message if message is not None else self.message


class ServerError(ApiError):
    pass


class ClientError(ApiError, ValueError):
    code = 400
    reason = "CLIENT_GENERIC"
    message = "Client Error"


class BadRequestError(ClientError):
    code = 400
    reason = "BAD_REQUEST_GENERIC"
    message = "Bad Request"


class InvalidJsonError(BadRequestError):
    reason = "INVALID_JSON"
    message = "Invalid JSON"


class UnauthorizedError(ClientError):
    code = 401
    reason = "UNAUTHORIZED_GENERIC"
    message = "Unauthorized"


class ForbiddenError(ClientError):
    code = 403
    reason = "FORBIDDEN_GENERIC"
    message = "Forbidden"


class NotFoundError(ClientError):
    code = 404
    reason = "NOT_FOUND_GENERIC"
    message = "Not Found"


class ConflictError(ClientError):
    code = 409
    reason = "CONFLICT_GENERIC"
    message = "Conflict"


class TooManyRequestsError(ClientError):
    code = 429
    reason = "TOO_MANY_REQUESTS_GENERIC"
    message = "Too Many Requests"


class UserInputError(ClientError):
    code = 499
    reason = "USER_INPUT_GENERIC"
    message = "User Input Error"


def ErrorResponse(e: ApiError):
    return JsonResponse(
        data={
            "success": False,
            "result": None,
            "error": {
                "code": e.code,
                "reason": e.reason,
                "message": e.message,
            },
        },
        status=e.code,
    )
