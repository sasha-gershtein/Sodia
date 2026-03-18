"""This file defines models (db tables) for app "interactions", their methods, and model managers to handle models.
This module is the single source of truth about what users are allowed and not allowed
to view/send in accordance with each other's privacy settings"""

import datetime
from enum import Enum, IntEnum, auto

from typing import Self
from uuid import UUID

from django.db import models, transaction
from django.db.models import Q, F, QuerySet
from django.db.models.functions import Least, Greatest
from django.utils import timezone

from Sodia.models import JsonEnumMixin, SingleChoiceField
from messaging.models import Dialogue
from settings.models import PrivacySetting
from users.models import User


class FriendRequestStatus(JsonEnumMixin, IntEnum):
    """enum class for friend request statuses"""
    PENDING = auto()  # a request has been sent but not responded to
    ACCEPTED = auto()  # a request has been sent and accepted (users are friends)
    DENIED = auto()  # a request has been sent and denied by receiver
    WITHDRAWN = auto()  # a request has been sent and withdrawn by sender
    REMOVED_BY_SENDER = auto()  # a request has been sent and accepted, but friend was later removed by sender
    REMOVED_BY_RECIPIENT = auto()  # a request has been sent and accepted, but friend was later removed by recipient


class FriendsManager(models.Manager):
    """manager for the FriendRequest model"""

    def get_queryset(self):
        """always select associated User rows when a Request row is selected
        to avoid unnecessarily duplicated db queries"""
        return super().get_queryset().select_related("sender", "recipient")

    def get_between(self, user_1: User, user_2: User, /):
        """get a friend request between two users, or return a dummy friend request object if request doesn't exist"""
        if user_1 == user_2:
            # a request between a user and themselves cannot exist
            raise ValueError("Users must be different")
        try:
            return self.get(
                Q(sender=user_1, recipient=user_2) |  # either sent by user_1
                Q(sender=user_2, recipient=user_1)  # or user_2
            )
        except self.model.DoesNotExist:
            return self.model(sender=user_1, recipient=user_2, status=None)  # return a dummy object not stored in db

    def check_friendship_between(self, user_1: User, user_2: User, /) -> bool:
        """check if users are friends"""
        return self.get_between(user_1, user_2).status == FriendRequestStatus.ACCEPTED

    def is_sendable_between(self, sender: User, recipient: User):
        """check if a request can be sent from sender to recipient"""
        return self.get_between(sender, recipient).is_resendable(sender)

    @transaction.atomic
    def send_request(self, sender: User, recipient: User):
        """send a friend request from sender to recipient"""
        request = self.get_between(sender, recipient)
        if not request.is_resendable(sender):
            # friend request cannot be sent
            raise ValueError(f"Cannot send friend request from {sender} to {recipient}")
        if request.pk is not None:
            # a request has existed (stored in db), so delete it to create new
            request.delete()
        return self.create(sender=sender, recipient=recipient)

    def update_pending_request(self, sender: User, recipient: User, status: FriendRequestStatus):
        """select a pending friend request from sender to recipient and set its status to the specified value.
        Can raise self.model.DoesNotExist if request doesn't exist"""
        request = self.get(sender=sender, recipient=recipient, status=FriendRequestStatus.PENDING)
        request.status = status
        request.save()

    def accept_request(self, sender: User, recipient: User):
        """accept a friend request from sender to recipient"""
        self.update_pending_request(sender, recipient, FriendRequestStatus.ACCEPTED)

    def deny_request(self, sender: User, recipient: User):
        """deny a friend request from sender to recipient"""
        self.update_pending_request(sender, recipient, FriendRequestStatus.DENIED)

    def withdraw_request(self, sender: User, recipient: User):
        """withdraw a friend request from sender to recipient"""
        self.update_pending_request(sender, recipient, FriendRequestStatus.WITHDRAWN)

    @transaction.atomic
    def remove_friend(self, user: User, friend: User):
        """remove a friend connection between user and friend"""
        request = self.get_between(user, friend)
        if request.status != FriendRequestStatus.ACCEPTED:
            raise self.model.DoesNotExist()

        # relation reset, so messaging back is disabled
        Dialogue.objects.reset_can_message_back(user, friend)

        if user == request.sender:
            request.status = FriendRequestStatus.REMOVED_BY_SENDER
        else:
            request.status = FriendRequestStatus.REMOVED_BY_RECIPIENT
        request.save()


class FriendRequest(models.Model):
    """model to store friend requests and connections"""
    REQUEST_COOLDOWN = datetime.timedelta(days=30)  # a repeated request can be sent again after 30 days

    sender = models.ForeignKey(User, related_name="requests_sent", on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name="requests_received", on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    status = SingleChoiceField(FriendRequestStatus, default=FriendRequestStatus.PENDING, null=True)

    objects = FriendsManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(  # unique request per unordered pair {sender, recipient} (enforced on db level)
                Least("sender", "recipient"),  # unique constraint automatically adds a search index
                Greatest("sender", "recipient"),
                name="unique_friend_request",
            ),
            models.CheckConstraint(
                condition=~Q(sender=F("recipient")),  # check that sender != recipient (enforced on db level)
                name="prevent_self_friend_request",
            ),
        ]

    def is_resendable(self, sender: User):
        """determine if a request can be sent between users (from sender)"""
        if self.status is None:
            # no requests have been sent between users before
            return True
        if self.status in (FriendRequestStatus.PENDING, FriendRequestStatus.ACCEPTED):
            # a pending request already exists or users are already friends
            return False
        if any(Block.objects.get_between(self.sender, self.recipient)):
            # one user is blocking another
            return False
        back = sender == self.recipient  # True if new request is to be sent by the old request's recipient
        if (  # can send if denied/removed by sender or withdrawn by receiver
                (self.status == FriendRequestStatus.DENIED and back)
                or
                (self.status == FriendRequestStatus.REMOVED_BY_SENDER and not back)
                or
                (self.status == FriendRequestStatus.REMOVED_BY_RECIPIENT and back)
                or
                (self.status == FriendRequestStatus.WITHDRAWN and back)
        ):
            return True
        # can only send if cooldown has passed
        return self.updated_at < timezone.now() - self.REQUEST_COOLDOWN


class BlockManager(models.Manager):
    """manager for the Block model"""

    def is_blocking(self, sender, recipient):
        """check if sender is blocking recipient"""
        return self.filter(sender=sender, recipient=recipient).exists()

    def get_between(self, user_1: User, user_2: User, /) -> tuple[bool, bool]:
        """check for blocks in both directions between user_1 and user_2"""
        return self.is_blocking(user_1, user_2), self.is_blocking(user_2, user_1)

    def block(self, sender: User, recipient: User):
        """block recipient by sender"""
        # remove friend connection or request between users if exists:
        request = FriendRequest.objects.get_between(sender, recipient)
        if request.status == FriendRequestStatus.ACCEPTED:
            sender.remove_friend(recipient)
        elif request.status == FriendRequestStatus.PENDING:
            if sender == request.sender:
                sender.withdraw_friend_request_to(recipient)
            else:
                sender.deny_friend_request_from(recipient)

        # relation reset, so messaging back is disabled
        Dialogue.objects.reset_can_message_back(sender, recipient)

        # block
        self.create(sender=sender, recipient=recipient)

    def unblock(self, sender: User, recipient: User):
        """unblock recipient by sender"""
        self.get(sender=sender, recipient=recipient).delete()


class Block(models.Model):
    """model to store blocks between users"""
    sender = models.ForeignKey(User, related_name="blocks_sent", on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name="blocks_received", on_delete=models.CASCADE)

    objects = BlockManager()

    class Meta:
        constraints = [
            # add a unique constraint on ordered (session, recipient) pair (automatically adds a search index)
            models.UniqueConstraint(fields=["sender", "recipient"], name="unique_block"),
            models.CheckConstraint(
                condition=~Q(sender=F("recipient")),  # check that sender != recipient (enforced on db level)
                name="prevent_self_block",
            ),
        ]


class Relation(Enum):
    """enum class for relation statuses between users"""
    SAME_USER = auto()
    FRIENDS = auto()
    PENDING_SENT = auto()  # user sent a friend request to related user
    PENDING_RECEIVED = auto()  # related user sent a friend request to user
    NONE = auto()
    FRIEND_REQUEST_FORBIDDEN = auto()
    # ^ there has been a failed (denied / withdrawn) friend request in the cooldown period,
    # due to which a new request cannot be sent at the moment
    # or user is blocked by related user
    BLOCKED = auto()  # related user is blocked by user

    def get_json_value(self):
        """return a JSON serializable value (member name as string)"""
        return self.name

    @classmethod
    def between(cls, user: User, related_user: User):
        """calculate the relation of user to related_user"""
        if user == related_user:
            return cls.SAME_USER
        if user.is_blocking(related_user):
            return cls.BLOCKED
        request = FriendRequest.objects.get_between(user, related_user)
        if request.status == FriendRequestStatus.ACCEPTED:
            return cls.FRIENDS
        if request.status == FriendRequestStatus.PENDING:
            # pending request is sent between users
            return cls.PENDING_SENT if user == request.sender else cls.PENDING_RECEIVED
        if not request.is_resendable(user):
            # new friend cannot be sent from user to related_user
            return cls.FRIEND_REQUEST_FORBIDDEN
        return cls.NONE

    @property
    def level(self):
        """get relation level (higher is stronger, 0 is default)"""
        match self:
            case Relation.SAME_USER:
                return 3
            case Relation.FRIENDS:
                return 2
            case Relation.PENDING_SENT | Relation.PENDING_RECEIVED:
                return 1
            case Relation.NONE:
                return 0
            case Relation.FRIEND_REQUEST_FORBIDDEN:
                return -1
            case Relation.BLOCKED:
                return -2
            case _:
                # unknown value, shouldn't happen
                raise ValueError("Undefined relation")

    def __ge__(self, other: Self | PrivacySetting):
        """check if self >= other.
        if other is a Relation, compare levels.
        if other is a PrivacySetting value, return True is self satisfies the minimum requirement of other"""
        if isinstance(other, Relation):
            return self.level >= other.level
        if isinstance(other, PrivacySetting):
            match other:
                case PrivacySetting.EVERYONE:
                    return True
                case PrivacySetting.FRIENDS_ONLY:
                    return self >= Relation.FRIENDS
                case PrivacySetting.NOBODY:
                    return self == Relation.SAME_USER
        return NotImplemented


class UserInfo:
    """class to store user info from perspective from another user.
    This class is the only source of truth to satisfy users' privacy settings"""
    PARTIAL = {  # fields included in partial user info api responses (usually used to display a user in a list)
        "id",
        "username",
        "is_activated",
        "first_name",
        "last_name",
        "display_name",
        "relation",
        "can_message",
        "unread_messages_count",
    }
    FULL = {  # fields included in full user info api responses (all fields, used to display user profiles)
        "id",
        "username",
        "is_activated",
        "first_name",
        "last_name",
        "display_name",
        "gender",
        "birth_date",
        "description",
        "challenge_streak",
        "year_group",
        "house",
        "boarding_type",
        "country",
        "relation",
        "friends_count",
        "friends_visible",
        "can_message",
        "unread_messages_count",
    }

    # lazy list of friends cache
    _friends: QuerySet[User] | None = None

    def __init__(self, user: User, requesting_user: User):
        """construct user info of user as seen by requesting_user"""
        self.user = user
        self.requesting_user = requesting_user

        relation = Relation.between(requesting_user, user)
        self.relation = relation

        account = user.account_settings
        privacy = user.privacy_settings

        self.id = user.id
        self.username = account.username
        self.is_activated = user.is_activated

        # store None if account setting is not set or isn't visible to requesting_user
        self.first_name = account.first_name if relation >= privacy.full_name else None
        self.last_name = account.last_name if relation >= privacy.full_name else None
        self.display_name = account.get_display_name()
        self.gender = account.gender
        self.birth_date = account.birth_date if relation >= privacy.birthday else None
        self.description = account.description if relation >= privacy.description else None

        self.challenge_streak = user.challenge_streak
        self.year_group = account.year_group
        self.house = account.house
        self.boarding_type = account.boarding_type
        self.country = account.country

        self.friends_count = self.user.get_friends().count()  # count of friends is always visible
        self.friends_visible = relation >= privacy.friends  # determine if the list of friends is visible

        if relation == Relation.SAME_USER:
            self.can_message = False  # cannot message self
            # for self-info, unread_messages_count is the number of unread messages received in total from all users
            self.unread_messages_count = self.user.unread_messages_count
        else:
            dialogue = Dialogue.objects.get_readonly_dialogue(requesting_user, user)
            self.can_message = (  # determine if messaging is allowed
                    user.is_activated and requesting_user.is_activated  # cannot message to/from deactivated accounts
                    and relation != Relation.BLOCKED  # cannot message a blocked user
                    and not user.is_blocking(requesting_user)  # cannot message if you are blocked
                    and (
                            relation >= privacy.message  # can message if privacy settings are satisfied
                            or dialogue.can_message_back  # or a message has been received and this is a reply
                            # or both users are pressing the Sodia Button
                            or (user.is_pressing_sodia_button and requesting_user.is_pressing_sodia_button)
                    )
            )
            # for non-self info, unread_messages_count is the number of unread messages received from user
            self.unread_messages_count = dialogue.unread_messages_count

    @property
    def friends(self):
        """friends of user"""
        if self.friends_visible and self._friends is None:
            # friends are visible and not yet cached
            self._friends = self.user.get_friends()  # cache resulting query set
        return self._friends  # return cached query set

    @staticmethod
    def normalise(value):
        """turn a field value into a JSON serializable value"""
        if isinstance(value, UUID):
            # serialize UUIDs as strings
            return str(value)
        return value  # keep all others values as they are

    def get_json_value(self, keys=None):
        """return a JSON serializable dict with defined fields from keys"""
        if keys is None:
            # by default, send partial info
            keys = self.PARTIAL
        return {
            # get JSON serializable value
            key: value.get_json_value() if hasattr(value, "get_json_value") else self.normalise(value)
            for key in keys  # for every specified key
            if (value := getattr(self, key)) is not None  # skip empty fields
        }

    @property
    def partial(self):
        """return partial user info"""
        return self.get_json_value(self.PARTIAL)

    @property
    def full(self):
        """return full user info"""
        return self.get_json_value(self.FULL)
