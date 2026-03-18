"""This file defines models (db tables) for app "settings", their methods, and model managers to handle models"""

import datetime
import re
from enum import IntFlag, auto

from django.db import models

from Sodia.models import FloatField, DateField, CharField, SingleChoiceField, MultipleChoiceField, JsonEnumMixin


class Country(models.Model):
    """static table listing world countries.
    Automatically populated by command "python manage.py init [--rewrite]\""""
    id = models.IntegerField(primary_key=True)  # explicit non-auto-increment id to control ids range
    name = CharField(max_length=100, unique=True)
    code = CharField(max_length=2, unique=True)

    def __str__(self):
        return self.name

    def get_json_value(self):
        """return a JSON serializable dict"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
        }


class HouseBoardingType(JsonEnumMixin, IntFlag):
    """JSON serializable enum flag for house boarding type"""
    BOARDING = auto()
    DAY = auto()
    MIXED = auto()  # house has both boarders and day students


class House(models.Model):
    """static table listing boarding/day Houses.
    Automatically populated by command "python manage.py init [--rewrite]\""""
    id = models.IntegerField(primary_key=True)  # explicit non-auto-increment id to control ids range
    name = models.CharField(max_length=20, unique=True)  # unique name enforced on db level (creates search index)
    boarding_type = SingleChoiceField(HouseBoardingType)

    def __str__(self):
        return self.name

    def get_json_value(self):
        """return a JSON serializable dict"""
        return {
            "id": self.id,
            "name": self.name,
            "boarding_type": self.boarding_type,
        }


class PupilBoardingType(JsonEnumMixin, IntFlag):
    """JSON serializable enum flag for pupil boarding type"""
    FULL = auto()
    WEEKLY = auto()
    DAY = auto()


class YearGroup(models.Model):
    """static table listing available year groups.
    Automatically populated by command "python manage.py init [--rewrite]\""""
    year_group_number = models.IntegerField(primary_key=True)  # explicit non-auto-increment id to control ids range
    name = CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    def get_json_value(self):
        """return a JSON serializable dict"""
        return {
            "id": self.year_group_number,
            "name": self.name,
        }


class SettingsManager(models.Manager):
    """[abstract] class for all managers for settings models.
    Can be used as-is or can be inherited from"""

    def get_queryset(self):
        """always select associated User row when a settings row is selected
        to avoid unnecessarily duplicated db queries"""
        return super().get_queryset().select_related("user")

    def activated(self):
        """filter settings rows of activated users only"""
        return self.filter(user__is_activated=True)


class AccountManager(SettingsManager):
    """manager for AccountSettings model"""

    def generate_username(self, email: str):
        """generate a unique username based on user's email"""
        max_length = self.model._meta.get_field("username").max_length
        # remove possible illegal characters: :/?#[]@!$&'()*+,;=
        base = re.sub(
            r"[^\w.\-_]", "", email.split("@")[0]  # take email's local-part (string before @)
        )[:max_length].lower()  # cut if too long and transform to lowercase
        username = base
        if len(base) < 2:  # base is too short or empty
            base = "user"  # give a default username
            username = "user-1"  # do not just give "user", start with "user-1"
        i = 2  # no suffix is equivalent to suffix "-1", so continue from 2
        while self.filter(username=username).exists():
            # username already taken
            suffix = f"-{i}"  # make a new suffix
            # add suffix to username without keeping max_length restriction
            username = base[:max_length - len(suffix)] + suffix
            i += 1  # next suffix count
        # username is unique, return username
        return username

    def create_account_settings(self, email, **kwargs):
        """create account settings (generate username based on email)"""
        username = self.generate_username(email)
        return self.create(username=username, **kwargs)

    def get_user_by_username(self, username: str, default=None, *, only_activated=True):
        """get user by username, return a default value if the user does not exist.
        By default, filters only activated user accounts, can be overridden with only_activated"""
        objects = self.activated() if only_activated else self.all()  # filter if required
        try:
            return objects.get(username=username).user
        except self.model.DoesNotExist:
            return default


class UserAccountSettings(models.Model):
    """model to store user's account settings"""
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="account_settings",
                                primary_key=True)
    # custom CharFields taking min_length and pattern:
    username = CharField(
        min_length=2, max_length=30,
        pattern=(
            r"^[\w.\-_]*$",
            "Username can only contain lowercase English letters, digits, periods, dashes and underscores"
        ),
        unique=True,
    )
    first_name = CharField(min_length=2, max_length=50)
    last_name = CharField(min_length=2, max_length=50)
    display_name = CharField(null=True, blank=True, min_length=5, max_length=100)
    gender = CharField(null=True, blank=True, max_length=30)
    # custom DateField taking min_value and max_value
    birth_date = DateField(null=True, blank=True, min_value=datetime.date(1900, 1, 1), max_value=datetime.date.today)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True, max_length=2000)
    house = models.ForeignKey(House, null=True, blank=True, on_delete=models.SET_NULL)
    boarding_type = SingleChoiceField(PupilBoardingType, null=True, blank=True)
    year_group = models.ForeignKey(YearGroup, null=True, blank=True, on_delete=models.SET_NULL)

    objects = AccountManager()

    def get_display_name(self):
        """return user's display name.
        Preferred name if specified and "Name Surname" otherwise"""
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} of {self.user}>"


class PrivacySetting(JsonEnumMixin, IntFlag):
    """JSON serializable enum flag for privacy settings choice"""
    EVERYONE = auto()  # information visible / action available for every user
    FRIENDS_ONLY = auto()  # information visible / action available for friends only
    NOBODY = auto()  # information not visible / action not available for other users


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

    objects = SettingsManager()  # use "default" settings' manager

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} of {self.user}>"


class UserNotificationsSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="notifications_settings",
                                primary_key=True)
    unread_messages = models.BooleanField(default=True)
    challenges_updates = models.BooleanField(default=True)
    new_friend_requests = models.BooleanField(default=True)
    accepted_friend_requests = models.BooleanField(default=True)
    sodia_button_updates = models.BooleanField(default=True)

    objects = SettingsManager()  # use "default" settings' manager

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} of {self.user}>"


class FrequencySetting(JsonEnumMixin, IntFlag):
    """JSON serializable enum flag for frequency settings choice"""
    IMMEDIATE = auto()
    DAY = auto()
    THREE_DAYS = auto()
    WEEK = auto()
    NEVER = auto()


class GenderFilter(JsonEnumMixin, IntFlag):
    """JSON serializable enum flag for gender filter settings choice"""
    MALE = auto()
    FEMALE = auto()
    OTHER = auto()
    ALL = MALE | FEMALE | OTHER


class UserChallengesSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="challenges_settings",
                                primary_key=True)
    frequency = SingleChoiceField(enum_class=FrequencySetting, default=FrequencySetting.THREE_DAYS)
    gender_filter = MultipleChoiceField(enum_class=GenderFilter, default=GenderFilter.ALL)
    # custom FloadFields taking min_value and max_value
    subjects_match = FloatField(default=0.0, min_value=-1.0, max_value=1.0)
    interests_match = FloatField(default=0.0, min_value=-1.0, max_value=1.0)

    objects = SettingsManager()  # use "default" settings' manager

    def __repr__(self):
        # return a human-readable representation for debug purposes
        return f"<{self.__class__.__name__} of {self.user}>"
