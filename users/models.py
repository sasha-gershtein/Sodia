from datetime import timedelta
from enum import IntFlag, auto
import secrets
import uuid

from .passwords import Password

from django.db import models, transaction
from django.utils import timezone

from Sodia.models import IntFlagField
from settings.models import UserAccountSettings, UserPrivacySettings, UserNotificationSettings, UserChallengesSettings


# TODO: make __str__
# TODO: add indexes

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
        UserNotificationSettings.objects.create(user=user)
        UserChallengesSettings.objects.create(user=user)
        return user


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_activated = models.BooleanField(default=False)
    flag = IntFlagField(enum_class=AccountFlag, exclusive_choices=True, default=AccountFlag.UNSAFE)
    # TODO: make separate table Challenge
    challenge_partner = models.OneToOneField("self", on_delete=models.SET_NULL, null=True, related_name="+")
    challenge_streak = models.IntegerField(default=0)
    is_pressing_sodia_button = models.BooleanField(default=False)

    objects = UserManager()


class PasswordField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 255)
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


class SessionManager(models.Manager):
    DEFAULT_TTL = timedelta(days=7)

    @classmethod
    def new_expires_at(cls):
        return timezone.now() + cls.DEFAULT_TTL

    @staticmethod
    def generate_session_token(self):
        return secrets.token_urlsafe(32)


class Session(models.Model):
    objects = SessionManager()

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, default=objects.generate_session_token, unique=True)
    last_request_ip = models.GenericIPAddressField()
    last_request_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=objects.new_expires_at)
    next_update_number = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "expires_at"]),
        ]

    def is_valid(self):
        return timezone.now() < self.expires_at


class SessionUpdate(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    update_number = models.IntegerField(default=0)
    update_message = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'update_number'], name='unique_session_update_number'),
        ]
