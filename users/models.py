from datetime import timedelta
from enum import IntFlag, auto
import secrets
import hashlib
import uuid
import hmac

from Sodia.settings import SECRET_KEY
from .passwords import Password

from django.db import models, transaction
from django.utils import timezone

from Sodia.models import IntFlagField
from settings.models import UserAccountSettings, UserPrivacySettings, UserNotificationsSettings, UserChallengesSettings


class AccountFlag(IntFlag):
    UNSAFE = auto()
    NEW = auto()
    SAFE = auto()


class UserManager(models.Manager):
    @transaction.atomic
    def create_user(self, *, first_name, last_name, email, password, **kwargs):
        user = self.create(**kwargs)
        UserLoginDetails.objects.create(user=user, email=email, password=password)
        username = email.split('@')[0][:UserAccountSettings._meta.get_field("username").max_length]
        UserAccountSettings.objects.create(user=user, username=username, first_name=first_name, last_name=last_name)
        UserPrivacySettings.objects.create(user=user)
        UserNotificationsSettings.objects.create(user=user)
        UserChallengesSettings.objects.create(user=user)
        return user


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_activated = models.BooleanField(default=False)
    flag = IntFlagField(enum_class=AccountFlag, is_multiple=True, default=AccountFlag.UNSAFE)
    # TODO: make separate table Challenge
    challenge_partner = models.OneToOneField("self", on_delete=models.SET_NULL, null=True, related_name="+")
    challenge_streak = models.IntegerField(default=0)
    is_pressing_sodia_button = models.BooleanField(default=False)

    objects = UserManager()

    def __repr__(self):
        return (f"<{self.__class__.__name__} {self.account_settings.get_display_name()} "
                f"(@{self.account_settings.username}, id: {self.id})>")

    def __str__(self):
        return f"{self.account_settings.get_display_name()} @{self.account_settings.username}"


class PasswordField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 128)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("max_length", None)
        return name, path, args, kwargs

    # noinspection PyMethodMayBeStatic
    def from_db_value(self, value, *_args, **_kwargs):
        if value is None:
            return value
        return Password.from_db_value(value)

    def to_python(self, value):
        if isinstance(value, Password) or value is None:
            return value
        return Password.from_password(value)

    def pre_save(self, model_instance, add):
        value = self.to_python(getattr(model_instance, self.attname))
        setattr(model_instance, self.attname, value)
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(value)


class UserLoginDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="login_details", primary_key=True)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_changed_at = models.DateTimeField(default=timezone.now)
    password = PasswordField()
    password_changed_at = models.DateTimeField(default=timezone.now)

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user} ({self.email})>"


class SessionManager(models.Manager):
    DEFAULT_TTL = timedelta(days=7)

    @classmethod
    def new_expires_at(cls):
        return timezone.now() + cls.DEFAULT_TTL

    @staticmethod
    def generate_session_token():
        return secrets.token_urlsafe(32)

    def create_session(self, **kwargs):
        token_plaintext = self.generate_session_token()
        token_hash = hmac.new(key=SECRET_KEY.encode("ascii"),
                              msg=token_plaintext.encode("ascii"),
                              digestmod=hashlib.sha256)
        kwargs["token"] = token_hash.digest()
        return token_plaintext, self.create(**kwargs)


class Session(models.Model):
    objects = SessionManager()

    token = models.BinaryField(unique=True, max_length=64)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    session_auth_hash = models.BinaryField(max_length=64, null=True)

    last_request_ip = models.GenericIPAddressField()
    last_request_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=objects.new_expires_at)
    next_update_number = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "expires_at"]),
        ]

    def get_auth_hash(self):
        signature = hmac.new(key=SECRET_KEY.encode("ascii"),
                             msg=self.user.login_details.password.password_hash + b":" + self.token,
                             digestmod=hashlib.sha256)
        return signature.digest()

    def expire(self):
        exp = self.expires_at < timezone.now()
        if exp:
            self.delete()
        return exp

    def renew(self, save=True):
        self.expires_at = Session.objects.new_expires_at()
        if save:
            self.save()

    def authenticate(self, user: User):
        self.user = user
        self.session_auth_hash = self.get_auth_hash()
        self.save()

    def logout(self):
        self.delete()

    def is_auth_valid(self):
        if self.expire() or self.user is None:
            return False
        if self.session_auth_hash is None:
            self.logout()
            return False
        if secrets.compare_digest(self.get_auth_hash(), self.session_auth_hash):
            return True
        self.logout()
        return False

    def __repr__(self):
        if self.user is None:
            return f"<{self.__class__.__name__} ({self.token[:20]}...)>"
        return f"<{self.__class__.__name__} ({self.token[:20]}...), auth: {self.user}>"


class SessionUpdate(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    update_number = models.IntegerField(default=0)
    update_message = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'update_number'], name='unique_session_update_number'),
        ]

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.update_number} of {self.session}>"
