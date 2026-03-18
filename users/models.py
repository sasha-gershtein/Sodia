"""This file defines models (db tables) for app "users", their methods, and model managers to handle models"""

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
    """Manager for the User model"""

    def get_queryset(self):
        """always select associated settings rows when a user's row is selected
        to avoid unnecessarily duplicated db queries"""
        return super().get_queryset().select_related(
            "account_settings", "privacy_settings", "notifications_settings", "challenges_settings"
        )

    @transaction.atomic
    def create_user(self, *, first_name, last_name, email, password, **kwargs):
        """create a user and associated settings db rows"""
        user = self.create(**kwargs)
        UserLoginDetails.objects.create(user=user, email=email, password=password)
        UserAccountSettings.objects.create_account_settings(email=email,  # email is used to generate username
                                                            user=user, first_name=first_name, last_name=last_name)
        UserPrivacySettings.objects.create(user=user)
        UserNotificationsSettings.objects.create(user=user)
        UserChallengesSettings.objects.create(user=user)
        return user  # return the created User object

    def activated(self):
        """filter only activated user accounts"""
        return self.filter(is_activated=True)

    def get_user_by_id(self, pk: str, default=None, *, only_activated=True):
        """get user by id (pk parameter), return a default value if the user does not exist.
        By default, filters only activated user accounts, can be overridden with only_activated"""
        objects = self.activated() if only_activated else self.all()  # filter if required
        try:
            return objects.get(pk=pk)
        except self.model.DoesNotExist:
            return default

    @staticmethod
    def get_user_by_username(username: str, default=None, *, only_activated=True):
        """get user by username, return a default value if the user does not exist.
        By default, filters only activated user accounts, can be overridden with only_activated"""
        # delegate to UserAccountSettings model's manager
        return UserAccountSettings.objects.get_user_by_username(username, default, only_activated=only_activated)

    @staticmethod
    def get_user_by_email(email: str, default=None, *, only_activated=True):
        """get user by email, return a default value if the user does not exist.
        By default, filters only activated user accounts, can be overridden with only_activated"""
        # delegate to UserLoginDetails model's manager
        return UserLoginDetails.objects.get_user_by_email(email, default, only_activated=only_activated)

    def get_user_by_data(self, data):
        """get user by data passed in an API request, identifying a user via id or username.
        If data is invalid or user is not found, raise appropriate API exceptions
        which are to be handled by the @api_view decorator"""
        if isinstance(pk := data.get("id"), str):
            # id is passed, get by id
            user = self.get_user_by_id(pk)
        elif isinstance(username := data.get("username"), str):
            # username is passed, get by username
            user = self.get_user_by_username(username)
        else:
            # neither is passed, request is malformed
            raise BadRequestError("User must be identified via id or username")
        if user is None:
            # user is not found
            raise NotFoundError("User does not exist", reason="USER_NOT_FOUND")
        return user

    def pressing_sodia_button(self):
        """get a query set of users who are pressing the Sodia Button"""
        return self.activated().filter(is_pressing_sodia_button=True)


class User(models.Model):
    """model to store main user information"""
    # uuid4 are used for ids to avoid information leakage through useer ids
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_activated = models.BooleanField(default=True)
    flag = SingleChoiceField(enum_class=AccountFlag, default=AccountFlag.UNSAFE)
    challenge_streak = models.IntegerField(default=0)  # unused value
    is_pressing_sodia_button = models.BooleanField(default=False)
    unread_messages_count = models.IntegerField(default=0)  # count of unread messages received in total

    objects = UserManager()

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return (f"<{self.__class__.__name__} {self.account_settings.get_display_name()} "
                f"(@{self.account_settings.username}, id: {self.id})>")

    def __str__(self):
        return f"{self.account_settings.get_display_name()} @{self.account_settings.username}"

    def info(self, requesting_user):
        """return info available to requesting_user"""
        from interactions.models import UserInfo  # local import to avoid circular imports
        return UserInfo(self, requesting_user)

    def get_friends(self):
        """get a query set of users who are friends with self"""
        from interactions.models import FriendRequest, FriendRequestStatus  # local import to avoid circular imports
        accepted = FriendRequest.objects.filter(status=FriendRequestStatus.ACCEPTED)  # all accepted friend request
        recipient_pks = accepted.filter(sender=self).values("recipient_id")  # ids of other in requests: self -> other
        sender_pks = accepted.filter(recipient=self).values("sender_id")  # ids of other in requests: other -> self
        return User.objects.activated().filter(
            Q(pk__in=recipient_pks) | Q(pk__in=sender_pks)  # return users with identified ids
        )

    def get_pending_sent(self):
        """get a query set of all sent friend requests which are currently pending"""
        from interactions.models import FriendRequestStatus  # local import to avoid circular imports
        return User.objects.activated().filter(
            requests_sent__status=FriendRequestStatus.PENDING,
            requests_sent__sender=self
        )

    def get_pending_received(self):
        """get a query set of all received friend requests which are currently pending"""
        from interactions.models import FriendRequestStatus  # local import to avoid circular imports
        return User.objects.activated().filter(
            requests_sent__status=FriendRequestStatus.PENDING,
            requests_sent__recipient=self
        )

    def is_friends_with(self, other: Self):
        """check if is friends with another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.check_friendship_between(self, other)

    def is_friend_request_sendable_to(self, recipient: Self):
        """check if a friend request can be sent to another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.is_sendable_between(self, recipient)

    def send_friend_request_to(self, recipient: Self):
        """send friend request to another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.send_request(self, recipient)

    def accept_friend_request_from(self, sender: Self):
        """accept friend request from another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.accept_request(sender, self)

    def deny_friend_request_from(self, sender: Self):
        """deny friend request from another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.deny_request(sender, self)

    def withdraw_friend_request_to(self, recipient: Self):
        """withdraw friend request sent to another user"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.withdraw_request(self, recipient)

    def remove_friend(self, friend: Self):
        """remove friend connection"""
        from interactions.models import FriendRequest  # local import to avoid circular imports
        return FriendRequest.objects.remove_friend(self, friend)

    def is_blocking(self, recipient: Self):
        """check if is blocking another user"""
        from interactions.models import Block  # local import to avoid circular imports
        return Block.objects.is_blocking(self, recipient)

    def block(self, recipient: Self):
        """block another user"""
        from interactions.models import Block  # local import to avoid circular imports
        return Block.objects.block(self, recipient)

    def unblock(self, recipient: Self):
        """unblock another user"""
        from interactions.models import Block  # local import to avoid circular imports
        return Block.objects.unblock(self, recipient)

    def search(self, query: str):
        """search users"""
        from .search import search  # local import to avoid circular imports
        return search(query, self)

    def get_dialogues(self):
        """get a query set of dialogues with other users"""
        return self.dialogues.order_by("last_message_sent_at")

    def get_unread_messages_count(self, interlocutor: Self):
        """get the count of unread messages received from a specified user"""
        from messaging.models import Dialogue  # local import to avoid circular imports
        return Dialogue.objects.get_unread_messages_count(self, interlocutor)

    def get_dialogue_messages(self, interlocutor: Self, start=0, n=10):
        """get messages in a specified ids range in a dialogue with interlocutor.
        messages are returned in reverse order of their position in the dialogue.
        the first message returned is with id strictly smaller than start (start should be the last fetched id)
        if start is 0, the first message returned is the last message sent in the dialogue
        n is the number of messages returned"""
        from messaging.models import Dialogue, Message  # local import to avoid circular imports
        return [
            message
            for message in Message.objects.get_dialogue_messages(
                Dialogue.objects.get_readonly_dialogue(self, interlocutor),
                start, n
            )
        ]

    @transaction.atomic  # transaction required to lock a Dialogue row
    def mark_dialogue_read(self, interlocutor: Self):
        """mark all messages in a dialogue with interlocutor as read"""
        from messaging.models import Dialogue  # local import to avoid circular imports
        try:
            Dialogue.objects.get_locked_dialogue(self, interlocutor).mark_read()  # lock a row to avoid race condition
        except Dialogue.DoesNotExist:
            # if dialogue doesn't exist, no error is returned
            pass

    def send_message(self, recipient: Self, content: str, *, exclude_session: "Session | None" = None):
        """send a message to another user and generate updates for all authorised sessions of self and recipient,
        excluding exclude_session (if not None), which is the session from which the message was sent"""
        from messaging.models import Dialogue  # local import to avoid circular imports
        return Dialogue.objects.send_message(self, recipient, content, exclude_session=exclude_session)

    def press_sodia_button(self):
        """press the Sodia Button"""
        self.is_pressing_sodia_button = True
        self.save()

    def unpress_sodia_button(self):
        """unpress (stop pressing) the Sodia Button"""
        self.is_pressing_sodia_button = False
        self.save()


class PasswordField(models.CharField):
    """CharField to store password hashes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, max_length=128, **kwargs)  # set max length for the db value

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("max_length", None)  # do not pass max_length to the constructor
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

    def pre_save(self, model_instance, add):  # hash password before saving to db
        value = self.to_python(getattr(model_instance, self.attname))  # take the field value from the model
        setattr(model_instance, self.attname, value)  # set the updated field value to the model
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(value)


class UserLoginDetailsManager(SettingsManager):  # inherits from settings.models.SettingsManager
    """Manager for the UserLoginDetails model"""

    def get_user_by_email(self, email: str, default=None, *, only_activated=True):
        """get user by email, return a default value if the user does not exist.
        By default, filters only activated user accounts, can be overridden with only_activated"""
        objects = self.activated() if only_activated else self.all()  # filter if required
        try:
            return objects.get(email=email).user
        except self.model.DoesNotExist:
            return default


class UserLoginDetails(models.Model):
    """model to store user's login details"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="login_details", primary_key=True)
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)  # unused
    email_changed_at = models.DateTimeField(default=timezone.now)
    password = PasswordField()
    password_changed_at = models.DateTimeField(default=timezone.now)

    objects = UserLoginDetailsManager()

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} of {self.user} ({self.email})>"


class SessionManager(models.Manager):
    DEFAULT_TTL = timedelta(days=7)  # session expires in a week unless renewed (on every request)

    @classmethod
    def new_expires_at(cls):
        """return a new expiry date measured from the current time"""
        return timezone.now() + cls.DEFAULT_TTL

    @staticmethod
    def generate_session_token():
        """generate a new random cryptographically secure session token"""
        return secrets.token_urlsafe(32)

    def create_session(self, **kwargs):
        """create a new session with a randomly generated token"""
        token_plaintext = self.generate_session_token()
        # hash the token
        token_hash = hmac.new(key=SECRET_KEY.encode("ascii"),  # use server's secret key to sign the token
                              msg=token_plaintext.encode("ascii"),
                              digestmod=hashlib.sha256)  # use the SHA-256 algorithm
        kwargs["token"] = token_hash.digest()
        return token_plaintext, self.create(**kwargs)  # return the plaintext token for cookies and the Session object

    def get_queryset(self):
        """always select the associated User row when a Session row is selected
        to avoid unnecessarily duplicated db queries"""
        return super().get_queryset().select_related("user")

    def get_by_token(self, token):
        """get a session by token hash"""
        return self.get(token=token)


class Session(models.Model):
    """model to store session information"""
    objects = SessionManager()

    token = models.BinaryField(unique=True, max_length=64)  # hash of the token stored in client's cookies
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)  # user authenticated to this session
    session_auth_hash = models.BinaryField(max_length=64, null=True)  # hash validating authentication

    last_request_ip = models.GenericIPAddressField()
    last_request_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=objects.new_expires_at)  # use default expiry time generated at creation
    # id of a next update for this session, or -1 if too many updates have been registered
    next_update_id = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["user", "expires_at"]),  # create indexes to search by user and by expiry time
        ]

    def get_auth_hash(self):
        """calculate hash to validate authentication.
        Sessions are automatically invalidated on password change by design.
        This is achieved by signing password hashes at authentication,
        and checking that passwords still sign to the same value at session authentication validation."""
        signature = hmac.new(key=SECRET_KEY.encode("ascii"),  # use server's secret key to sign password hash and token
                             # auth hash is unique to the session token and the password at authentication
                             msg=self.user.login_details.password.password_hash + b":" + self.token,
                             digestmod=hashlib.sha256)  # use the SHA-256 algorithm
        return signature.digest()

    def expire(self):
        """check if session has expired and delete row from db if so"""
        expired = self.expires_at < timezone.now()
        if expired:
            self.delete()
        return expired

    def renew(self, save=True):
        """move expiry date forward and save to db if save=True"""
        self.expires_at = Session.objects.new_expires_at()
        if save:
            self.save()

    def authenticate(self, user: User):
        """authenticate a user to the session"""
        self.user = user  # attach a user
        self.session_auth_hash = self.get_auth_hash()  # calculate and store authentication hash
        self.save()

    def logout(self):
        """logout a user.
        Sessions are deleted on logout so that two different users cannot ever share the same session"""
        self.delete()

    def is_auth_valid(self):
        """check if authentication is valid"""
        if self.expire() or self.user is None:
            # the session has expired or has not been authenticated in the first place
            return False
        if self.session_auth_hash is None:
            # auth hash has to be defined if user is authenticated, otherwise force logout
            self.logout()
            return False
        # compare stored authentication hash with what would be a current hash
        # using constant-time comparison to prevent timing attacks
        if secrets.compare_digest(self.get_auth_hash(), self.session_auth_hash):
            return True
        self.logout()
        return False

    def __repr__(self):
        # return a human-readable representation for debug purposes
        if self.user is None:
            return f"<{self.__class__.__name__} ({self.token[:20]}...)>"
        return f"<{self.__class__.__name__} ({self.token[:20]}...), auth: {self.user}>"
