import datetime
import re
from enum import IntFlag, auto

from django.db import models

from Sodia.models import FloatField, DateField, CharField, SingleChoiceField, MultipleChoiceField, JsonEnumMixin


# Create your models here.
class Country(models.Model):  # TODO: populate
    name = CharField(max_length=100)
    code = CharField(max_length=2, unique=True)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
        }


class HouseBoardingType(JsonEnumMixin, IntFlag):
    BOARDING = auto()
    DAY = auto()
    MIXED = auto()


class House(models.Model):  # TODO: populate
    name = models.CharField(max_length=20)
    boarding_type = SingleChoiceField(HouseBoardingType)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return {
            "id": self.id,
            "name": self.name,
            "boarding_type": self.boarding_type,
        }


class PupilBoardingType(JsonEnumMixin, IntFlag):
    FULL = auto()
    WEEKLY = auto()
    DAY = auto()


class YearGroup(models.Model):
    year_group_number = models.IntegerField(primary_key=True)
    name = CharField(max_length=20)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return {
            "id": self.year_group_number,
            "name": self.name,
        }


class SettingsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related("user")

    def activated(self):
        return self.filter(user__is_activated=True)


class AccountManager(SettingsManager):
    def generate_username(self, email: str):
        max_length = self.model._meta.get_field("username").max_length
        # remove possible illegal characters: :/?#[]@!$&'()*+,;=
        base = re.sub(
            r"[^\w.\-_]", "", email.split('@')[0]
        )[:max_length]
        username = base
        if len(base) < 2:
            base = "user"
            username = "user-1"
        i = 2
        while self.filter(username=username).exists():
            suffix = f"-{i}"
            username = base[:max_length - len(suffix)] + suffix
            i += 1
        return username

    def create_account_settings(self, email, **kwargs):
        username = self.generate_username(email)
        return self.create(username=username, **kwargs)

    def get_user_by_username(self, username: str, default=None, *, only_activated=True):
        objects = self.activated() if only_activated else self.all()
        try:
            user = objects.get(username=username).user
        except self.model.DoesNotExist:
            user = default
        return user


class UserAccountSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name='account_settings',
                                primary_key=True)
    username = CharField(
        min_length=2, max_length=30,
        pattern=(
            r"^[\w.\-_]*$",
            "Username can only contain English letters, digits, periods, dashes and underscores"
        ),
        unique=True
    )  # TODO: set lowercase
    first_name = CharField(min_length=2, max_length=50)
    last_name = CharField(min_length=2, max_length=50)
    display_name = CharField(null=True, blank=True, min_length=5, max_length=100)
    # profile_picture = models.??? TODO
    gender = CharField(null=True, blank=True, max_length=30)  # TODO: set lowercase
    birth_date = DateField(null=True, blank=True, min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True, max_length=2000)
    house = models.ForeignKey(House, null=True, blank=True, on_delete=models.SET_NULL)
    boarding_type = SingleChoiceField(PupilBoardingType, null=True, blank=True)  # TODO: must be NULL if house is NULL
    year_group = models.ForeignKey(YearGroup, null=True, blank=True, on_delete=models.SET_NULL)
    # free_periods = ??? TODO: JSONField

    objects = AccountManager()

    def get_display_name(self):
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"


class PrivacySetting(JsonEnumMixin, IntFlag):
    EVERYONE = auto()
    FRIENDS_ONLY = auto()
    NOBODY = auto()


class UserPrivacySettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="privacy_settings",
                                primary_key=True)
    full_name = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.EVERYONE)
    profile_picture = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.EVERYONE)
    birthday = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.EVERYONE)
    free_periods = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.FRIENDS_ONLY)
    interests = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.EVERYONE)
    description = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.EVERYONE)
    friends = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.FRIENDS_ONLY)
    message = SingleChoiceField(enum_class=PrivacySetting, default=PrivacySetting.FRIENDS_ONLY)

    objects = SettingsManager()

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"


class UserNotificationsSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="notifications_settings",
                                primary_key=True)
    unread_messages = models.BooleanField(default=True)
    challenges_updates = models.BooleanField(default=True)
    new_friend_requests = models.BooleanField(default=True)
    accepted_friend_requests = models.BooleanField(default=True)
    sodia_button_updates = models.BooleanField(default=True)

    objects = SettingsManager()

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"


class FrequencySetting(JsonEnumMixin, IntFlag):
    IMMEDIATE = auto()
    DAY = auto()
    THREE_DAYS = auto()
    WEEK = auto()
    NEVER = auto()


class GenderFilter(JsonEnumMixin, IntFlag):
    MALE = auto()
    FEMALE = auto()
    OTHER = auto()
    ALL = MALE | FEMALE | OTHER


class UserChallengesSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="challenges_settings",
                                primary_key=True)
    frequency = SingleChoiceField(enum_class=FrequencySetting, default=FrequencySetting.THREE_DAYS)
    # year_groups = TODO: JSONField
    gender_filter = MultipleChoiceField(enum_class=GenderFilter, default=GenderFilter.ALL)
    subjects_match = FloatField(default=0.0, min_value=-1.0, max_value=1.0)
    interests_match = FloatField(default=0.0, min_value=-1.0, max_value=1.0)

    objects = SettingsManager()

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"
