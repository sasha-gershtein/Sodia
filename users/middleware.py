from django.http import HttpRequest, HttpResponse

from .models import Session


class AuthData:
    def __init__(self, session=None, user=None):
        self.session = session
        self.user = user


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = None
        session_token = request.COOKIES.get("auth")
        if not session_token:
            return self.get_response(request)
        try:
            session = Session.objects.select_related("user").get(token=session_token)
        except Session.DoesNotExist:
            session = None
        if session:
            if session.is_valid():
                session.last_request_ip = get_client_ip(request)
                session.expire_at = Session.objects.new_expires_at()
                session.save()
                user = session.user
            else:
                session.delete()
                session = None

        request.auth = AuthData(session=session, user=user)
        response: HttpResponse = self.get_response(request)
        if session_token and session is None:
            if not response.cookies.get("auth"):
                response.delete_cookie("auth")
        return response
