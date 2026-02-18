from dataclasses import dataclass
from enum import Enum, auto
from typing import Self

from django.db import models

from settings.models import PrivacySetting
from users.models import User


class Relation(Enum):
    SAME_USER = auto()
    FRIENDS = auto()
    PENDING_SENT = auto()  # user sent a friend request to related user
    PENDING_RECEIVED = auto()  # related user sent a friend request to user
    NONE = auto()
    FAILED_REQUEST = auto()  # there has been a failed (denied / withdrawn) friend request in the past three months
    BLOCKED = auto()  # related user is blocked by user

    def get_json_value(self):
        return str(self.name)

    @classmethod
    def between(cls, user: User, related_user: User):
        if user == related_user:
            return cls.SAME_USER
        return cls.NONE  # TODO

    @property
    def level(self):
        match self:
            case Relation.SAME_USER:
                return 3
            case Relation.FRIENDS:
                return 2
            case Relation.PENDING_SENT, Relation.PENDING_RECEIVED:
                return 1
            case Relation.NONE:
                return 0
            case Relation.FAILED_REQUEST:
                return -1
            case Relation.BLOCKED:
                return -2

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


@dataclass
class UserInfo:
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

        self.can_message = relation >= privacy.message  # TODO
