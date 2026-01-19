from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse

from .models import Session, User

@dataclass
class SessionData:
    session: Session | None = None
    is_session_new: bool = False
    user: User | None = None


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get("REMOTE_ADDR")


class SessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        session: Session | None = None
        is_session_new = False
        token = request.COOKIES.get("auth")
        if token:
            try:
                session = Session.objects.select_related("user").get(token=token)
                if session.expire():
                    session = None
            except Session.DoesNotExist:
                pass
        if session is None:
            session = Session.objects.create(last_request_ip=get_client_ip(request))
            is_session_new = True
        else:
            session.last_request_ip = get_client_ip(request)
            session.renew(save=True)

        request.session_data = SessionData(session=session, is_session_new=is_session_new)
        response: HttpResponse = self.get_response(request)
        if request.session_data.is_session_new:
            response.set_cookie(key="auth", value=session.token, httponly=True)
        return response


class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        session_data: SessionData = request.session_data
        user = session_data.session.user
        if user is not None:
            if session_data.session.is_auth_valid():
                session_data.user = user
            else:
                session_data.session = Session.objects.create(last_request_ip=get_client_ip(request))
                session_data.is_session_new = True

        return self.get_response(request)
