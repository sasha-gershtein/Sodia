"""This file defines middleware handling sessions and user authentication"""

import hashlib
import hmac
from dataclasses import dataclass

from django.http import HttpRequest, HttpResponse

from Sodia.settings import SECRET_KEY
from .models import Session, User


@dataclass
class SessionData:
    """This class stores information about a session and user authentication.
    An instance is attached to every request object going through the middleware"""
    session: Session | None = None
    # if a new cookie needs to be set, its value is passed to SessionMiddleware through session_token_plaintext
    session_token_plaintext: str | None = None
    user: User | None = None


def get_client_ip(request):
    """Returns the client ip of the current request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class SessionMiddleware:
    """Middleware that generates sessions for every request and handles session cookies"""

    def __init__(self, get_response):
        # get_response is a function that gives control to Django to run the inner layers of request processing
        # i.e. call inner middlewares, match a view by path, run the view, and return the response
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process a request"""
        session: Session | None = None
        token_plaintext = request.COOKIES.get("auth")
        if token_plaintext:
            # hash token to find the hashed value in the database
            token_hash = hmac.new(key=SECRET_KEY.encode("ascii"),  # use server's secret key to sign tokens
                                  msg=token_plaintext.encode("ascii"),
                                  digestmod=hashlib.sha256).digest()  # use the SHA-256 algorithm
            try:
                session = Session.objects.get_by_token(token_hash)
            except Session.DoesNotExist:
                pass
            else:
                if session.expire():  # check if session is expired and, if so, delete it
                    session = None  # if it is expired, there's no valid session
        if session is None:
            # if there's no valid session, generate a new session
            token_plaintext, session = Session.objects.create_session(last_request_ip=get_client_ip(request))
        else:
            # there is a valid session
            session.last_request_ip = get_client_ip(request)  # update metadata
            session.renew(save=True)  # renew the session (move expiry date forward) and save

        # attach session information to the request object
        request.session_data = SessionData(session=session, session_token_plaintext=token_plaintext)
        # get response from a view matched to this request
        response: HttpResponse = self.get_response(request)
        if request.session_data.session_token_plaintext:
            # a token is set (either old token renewed, or a new generated in this function or by an inner process)
            response.set_cookie(key="auth", value=token_plaintext, httponly=True, samesite="Lax", path="/",
                                expires=request.session_data.session.expires_at)  # set a client cookie
        else:
            response.delete_cookie("auth")  # session is removed (e.g. on logout), so clear cookie
        return response


class AuthenticationMiddleware:
    """Middleware to authenticate users and attach to sessions"""

    def __init__(self, get_response):
        # get_response is a function that gives control to Django to run the inner layers of request processing
        # i.e. call inner middlewares, match a view by path, run the view, and return the response
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        session_data: SessionData = request.session_data
        user = session_data.session.user
        if user is not None:
            # a user is associated with the session
            if session_data.session.is_auth_valid():  # check if authentication is still valid
                session_data.user = user  # set authenticated user
            else:
                # authentication is invalid, so best to create a new session
                session_data.session_token_plaintext, session_data.session = Session.objects.create_session(
                    last_request_ip=get_client_ip(request)
                )

        return self.get_response(request)  # run inner layers and return response
