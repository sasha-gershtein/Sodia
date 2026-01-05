from django.http import JsonResponse


class ApiError(Exception):
    code: int = 500
    message: str = "Internal Server Error"

    def __init__(self, message=None, *args, code=None):
        super().__init__(*args)
        self.code = code if code is not None else self.code
        self.message = message if message is not None else self.message


class ServerError(ApiError):
    pass


class ClientError(ApiError, ValueError):
    code = 400
    message = "Client Error"


class BadRequestError(ClientError):
    code = 400
    message = "Bad Request"


class InvalidJsonError(BadRequestError):
    message = "Invalid JSON"


class UnauthorizedError(ClientError):
    code = 401
    message = "Unauthorized"


class ForbiddenError(ClientError):
    code = 403
    message = "Forbidden"


class NotFoundError(ClientError):
    code = 404
    message = "Not Found"


class ConflictError(ClientError):
    code = 409
    message = "Conflict"


class TooManyRequestsError(ClientError):
    code = 429
    message = "Too Many Requests"


class UserInputError(ClientError):
    code = 499
    message = "User Input Error"


def ErrorResponse(e: ApiError):
    return JsonResponse(
        data={
            "success": False,
            "result": None,
            "error": {
                "code": e.code,
                "message": e.message,
            },
        },
        status=e.code,
    )