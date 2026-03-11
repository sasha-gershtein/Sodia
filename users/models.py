from datetime import timedelta
from enum import IntFlag, auto
import secrets
import hashlib
import uuid
import hmac

from typing import Self

from .passwords import Password
from Sodia.settings import SECRET_KEY
from Sodia.models import SingleChoiceField
from settings.models import (
    UserAccountSettings, UserPrivacySettings, UserNotificationsSettings, UserChallengesSettings, SettingsManager
)

from api.errors import BadRequestError, NotFoundError

from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


class AccountFlag(IntFlag):
    UNSAFE = auto()
    NEW = auto()
    SAFE = auto()


class UserManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            "account_settings", "privacy_settings", "notifications_settings", "challenges_settings"
        )

    @transaction.atomic
    def create_user(self, *, first_name, last_name, email, password, **kwargs):
        user = self.create(**kwargs)
        UserLoginDetails.objects.create(user=user, email=email, password=password)
        UserAccountSettings.objects.create_account_settings(email=email,
                                                            user=user, first_name=first_name, last_name=last_name)
        UserPrivacySettings.objects.create(user=user)
        UserNotificationsSettings.objects.create(user=user)
        UserChallengesSettings.objects.create(user=user)
        return user

    def activated(self):
        return self.filter(is_activated=True)

    def get_user_by_id(self, pk: str, default=None, *, only_activated=True):
        objects = self.activated() if only_activated else self.all()
        try:
            user = objects.get(pk=pk)
        except self.model.DoesNotExist:
            user = default
        return user

    @staticmethod
    def get_user_by_username(username: str, default=None, *, only_activated=True):
        return UserAccountSettings.objects.get_user_by_username(username, default, only_activated=only_activated)

    @staticmethod
    def get_user_by_email(email: str, default=None, *, only_activated=True):
        return UserLoginDetails.objects.get_user_by_email(email, default, only_activated=only_activated)

    def get_user_by_data(self, data):
        if isinstance(pk := data.get("id"), str):
            user = self.get_user_by_id(pk)
        elif isinstance(username := data.get("username"), str):
            user = self.get_user_by_username(username)
        else:
            raise BadRequestError("User must be identified via id or username")
        if user is None:
            raise NotFoundError("User does not exist", reason="USER_NOT_FOUND")
        return user


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_activated = models.BooleanField(default=True)  # TODO: default should be False
    flag = SingleChoiceField(enum_class=AccountFlag, default=AccountFlag.UNSAFE)
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

    def info(self, requesting_user):
        from interactions.models import UserInfo
        return UserInfo(self, requesting_user)

    def get_friends(self):
        from interactions.models import FriendRequest, FriendRequestStatus
        accepted = FriendRequest.objects.filter(status=FriendRequestStatus.ACCEPTED)
        recipient_pks = accepted.filter(sender=self).values("recipient_id")
        sender_pks = accepted.filter(recipient=self).values("sender_id")
        return User.objects.activated().filter(
            Q(pk__in=recipient_pks) | Q(pk__in=sender_pks)
        )

    def get_pending_sent(self):
        from interactions.models import FriendRequestStatus
        return User.objects.activated().filter(
            requests_sent__status=FriendRequestStatus.PENDING,
            requests_sent__sender=self
        )

    def get_pending_received(self):
        from interactions.models import FriendRequestStatus
        return User.objects.activated().filter(
            requests_sent__status=FriendRequestStatus.PENDING,
            requests_sent__recipient=self
        )

    def is_friends_with(self, other: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.check_friendship_between(self, other)

    def is_friend_request_sendable_to(self, recipient: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.is_sendable_between(self, recipient)

    def send_friend_request_to(self, recipient: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.send_request(self, recipient)

    def accept_friend_request_from(self, sender: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.accept_request(sender, self)

    def deny_friend_request_from(self, sender: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.deny_request(sender, self)

    def withdraw_friend_request_to(self, recipient: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.withdraw_request(self, recipient)

    def remove_friend(self, friend: Self):
        from interactions.models import FriendRequest
        return FriendRequest.objects.remove_friend(self, friend)

    def is_blocking(self, recipient: Self):
        from interactions.models import Block
        return Block.objects.is_blocking(self, recipient)

    def block(self, recipient: Self):
        from interactions.models import Block
        return Block.objects.block(self, recipient)

    def unblock(self, recipient: Self):
        from interactions.models import Block
        return Block.objects.unblock(self, recipient)

    def search(self, query: str):
        from .search import search
        return search(query, self)

    def get_dialogues(self):
        return self.dialogues.order_by("last_message_sent_at")

    def get_unread_messages_count(self, interlocutor: Self):
        from messaging.models import Dialogue
        return Dialogue.objects.get_unread_messages_count(self, interlocutor)

    def get_dialogue_messages(self, interlocutor: Self, start=0, n=10):
        from messaging.models import Dialogue, Message
        return [
            message
            for message in Message.objects.get_dialogue_messages(
                Dialogue.objects.get_readonly_dialogue(self, interlocutor),
                start, n
            )
        ]

    def mark_dialogue_read(self, interlocutor: Self):
        from messaging.models import Dialogue
        Dialogue.objects.get_dialogue(self, interlocutor).mark_read()

    def send_message(self, recipient: Self, content: str, *, exclude_session: "Session | None" = None):
        from messaging.models import Dialogue
        return Dialogue.objects.send_message(self, recipient, content, exclude_session=exclude_session)


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


class UserLoginDetailsManager(SettingsManager):
    def get_user_by_email(self, email: str, default=None, *, only_activated=True):
        objects = self.activated() if only_activated else self.all()
        try:
            user = objects.get(email=email).user
        except self.model.DoesNotExist:
            user = default
        return user


class UserLoginDetails(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="login_details", primary_key=True)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_changed_at = models.DateTimeField(default=timezone.now)
    password = PasswordField()
    password_changed_at = models.DateTimeField(default=timezone.now)

    objects = UserLoginDetailsManager()

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
    next_update_id = models.IntegerField(default=0)

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
