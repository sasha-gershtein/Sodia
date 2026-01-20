import hashlib
import hmac
from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse

from Sodia.settings import SECRET_KEY
from .models import Session, User


@dataclass
class SessionData:
    session: Session | None = None
    session_token_plaintext: str | None = None
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
        token_plaintext = request.COOKIES.get("auth")
        if token_plaintext:
            token_hash = hmac.new(key=SECRET_KEY.encode("ascii"),
                                  msg=token_plaintext.encode("ascii"),
                                  digestmod=hashlib.sha256).digest()
            try:
                session = Session.objects.select_related("user").get(token=token_hash)
                if session.expire():
                    session = None
            except Session.DoesNotExist:
                pass
        if session is None:
            token_plaintext, session = Session.objects.create_session(last_request_ip=get_client_ip(request))
        else:
            session.last_request_ip = get_client_ip(request)
            session.renew(save=True)

        request.session_data = SessionData(session=session, session_token_plaintext=token_plaintext)
        response: HttpResponse = self.get_response(request)
        if request.session_data.session_token_plaintext:
            response.set_cookie(key="auth", value=token_plaintext, httponly=True, samesite="Lax", path="/",
                                expires=request.session_data.session.expires_at)
        else:
            response.delete_cookie("auth")
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
                session_data.session_token_plaintext, session_data.session = Session.objects.create_session(
                    last_request_ip=get_client_ip(request)
                )

        return self.get_response(request)
