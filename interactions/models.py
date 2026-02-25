import datetime
from enum import Enum, IntEnum, auto

from typing import Self

from django.db import models, transaction
from django.db.models import Q, F
from django.db.models.functions import Least, Greatest
from django.utils import timezone

from Sodia.models import JsonEnumMixin, SingleChoiceField
from settings.models import PrivacySetting
from users.models import User

from api.errors import ConflictError


class FriendRequestStatus(JsonEnumMixin, IntEnum):
    PENDING = auto()
    ACCEPTED = auto()
    DENIED = auto()
    WITHDRAWN = auto()
    REMOVED_BY_SENDER = auto()
    REMOVED_BY_RECIPIENT = auto()


class FriendsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("sender", "recipient")

    def get_between(self, user_1: User, user_2: User):
        if user_1 == user_2:
            raise ValueError("Users must be different")
        try:
            return self.get(
                Q(sender=user_1, recipient=user_2) |
                Q(sender=user_2, recipient=user_1)
            )
        except self.model.DoesNotExist:
            return self.model(sender=user_1, recipient=user_2, status=None)
        except self.model.MultipleObjectsReturned as e:
            raise AssertionError("Database in illegal state. There must be a unique request between users") from e

    def check_friendship_between(self, user_1: User, user_2: User, /) -> bool:
        request = self.get_between(user_1, user_2)

        return request.status == FriendRequestStatus.ACCEPTED

    def is_sendable_between(self, sender: User, recipient: User):
        return self.get_between(sender, recipient).is_resendable(sender)

    @transaction.atomic
    def send_request(self, sender: User, recipient: User, *, is_api=False):
        request = self.get_between(sender, recipient)
        if not request.is_resendable(sender):
            if is_api:
                raise ConflictError(f"Could not send a friend request. Please try refreshing the page",
                                    reason="FRIEND_REQUEST_NOT_SENDABLE")
            raise ValueError(f"Cannot send friend request from {sender} to {recipient}")
        if request.pk is not None:
            request.delete()
        return self.create(sender=sender, recipient=recipient)

    def update_pending_request(self, sender: User, recipient: User, status: FriendRequestStatus):
        request = self.get(sender=sender, recipient=recipient, status=FriendRequestStatus.PENDING)
        request.status = status
        request.save()

    def accept_request(self, sender: User, recipient: User):
        self.update_pending_request(sender, recipient, FriendRequestStatus.ACCEPTED)

    def deny_request(self, sender: User, recipient: User):
        self.update_pending_request(sender, recipient, FriendRequestStatus.DENIED)

    def withdraw_request(self, sender: User, recipient: User):
        self.update_pending_request(sender, recipient, FriendRequestStatus.WITHDRAWN)

    def remove_friend(self, user: User, friend: User):
        request = self.get_between(user, friend)
        if request.status != FriendRequestStatus.ACCEPTED:
            raise self.model.DoesNotExist
        if user == request.sender:
            request.status = FriendRequestStatus.REMOVED_BY_SENDER
        else:
            request.status = FriendRequestStatus.REMOVED_BY_RECIPIENT
        request.save()


class FriendRequest(models.Model):
    REQUEST_COOLDOWN = datetime.timedelta(days=30 * 3)

    sender = models.ForeignKey(User, related_name="requests_sent", on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name="requests_received", on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True)
    status = SingleChoiceField(FriendRequestStatus, default=FriendRequestStatus.PENDING, null=True)

    objects = FriendsManager()

    class Meta:
        constraints = [
            # models.UniqueConstraint(fields=['sender', 'recipient'], name='unique_friend_request'),
            models.UniqueConstraint(
                Least("sender", "recipient"),
                Greatest("sender", "recipient"),
                name="unique_friend_request",
            ),
            models.CheckConstraint(
                condition=~Q(sender=F('recipient')),
                name='prevent_self_friend_request',
            ),
        ]

    def is_resendable(self, sender: User):
        if self.status is None:
            return True
        if self.status in (FriendRequestStatus.PENDING, FriendRequestStatus.ACCEPTED):
            return False
        back = sender == self.recipient
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
        return self.updated_at < timezone.now() - self.REQUEST_COOLDOWN


class Relation(Enum):
    SAME_USER = auto()
    FRIENDS = auto()
    PENDING_SENT = auto()  # user sent a friend request to related user
    PENDING_RECEIVED = auto()  # related user sent a friend request to user
    NONE = auto()
    FAILED_REQUEST = auto()  # there has been a failed (denied / withdrawn) friend request in the cooldown period,
    #                          due to which a new request cannot be sent at the moment
    BLOCKED = auto()  # related user is blocked by user

    def get_json_value(self):
        return str(self.name)

    @classmethod
    def between(cls, user: User, related_user: User):
        if user == related_user:
            return cls.SAME_USER
        if False:
            return cls.BLOCKED  # noqa TODO
        request = FriendRequest.objects.get_between(user, related_user)
        if request.status == FriendRequestStatus.ACCEPTED:
            return cls.FRIENDS
        if request.status == FriendRequestStatus.PENDING:
            return cls.PENDING_SENT if user == request.sender else cls.PENDING_RECEIVED
        if not request.is_resendable(user):
            return cls.FAILED_REQUEST
        return cls.NONE

    @property
    def level(self):
        match self:
            case Relation.SAME_USER:
                return 3
            case Relation.FRIENDS:
                return 2
            case Relation.PENDING_SENT | Relation.PENDING_RECEIVED:
                return 1
            case Relation.NONE:
                return 0
            case Relation.FAILED_REQUEST:
                return -1
            case Relation.BLOCKED:
                return -2
            case _:
                raise ValueError("Undefined relation")

    def __ge__(self, other: Self | PrivacySetting):
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
    PARTIAL = {
        "id",
        "username",
        "first_name",
        "last_name",
        "display_name",
        "relation",
        "can_message",
    }
    FULL = {
        "id",
        "username",
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
        "can_message",
    }

    _friends: list[User] | None = None

    def __init__(self, user: User, requesting_user: User):
        self.user = user
        self.requesting_user = requesting_user

        relation = Relation.between(requesting_user, user)
        self.relation = relation

        account = user.account_settings
        privacy = user.privacy_settings

        self.id = user.id
        self.username = account.username

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

        self.friends_visible = relation >= privacy.friends
        self.can_message = relation >= privacy.message  # TODO

    @property
    def friends(self):
        if self.friends_visible and self._friends is None:
            self._friends = self.user.get_friends()
        return self._friends

    def get_json_value(self, keys=None):
        if keys is None:
            keys = self.PARTIAL
        return {
            key: value.get_json_value() if hasattr(value, "get_json_value") else value
            for key in keys
            if (value := getattr(self, key)) is not None
        }

    @property
    def partial(self):
        return self.get_json_value(self.PARTIAL)

    @property
    def full(self):
        return self.get_json_value(self.FULL)