from enum import IntFlag, auto

from django.core.validators import MinLengthValidator
from django.db import models

from Sodia.models import MultipleChoiceField, SingleChoiceField


# Create your models here.
class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return self.id


class HouseBoardingType(IntFlag):
    BOARDING = auto()
    DAY = auto()
    MIXED = auto()


class House(models.Model):
    name = models.CharField(max_length=20)
    boarding_type = SingleChoiceField(HouseBoardingType)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return self.id


class PupilBoardingType(IntFlag):
    FULL = auto()
    WEEKLY = auto()
    DAY = auto()


class YearGroup(models.Model):
    year_group_number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    def get_json_value(self):
        return self.year_group_number


class UserAccountSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name='account_settings',
                                primary_key=True)
    username = models.CharField(max_length=30, validators=[MinLengthValidator(4)], unique=True)
    first_name = models.CharField(max_length=50, validators=[MinLengthValidator(2)])
    last_name = models.CharField(max_length=50, validators=[MinLengthValidator(2)])
    display_name = models.CharField(null=True, blank=True, max_length=100, validators=[MinLengthValidator(5)])
    is_full_name_hidden = models.BooleanField(default=False)
    # profile_picture = models.??? TODO
    gender = models.CharField(null=True, blank=True, max_length=30)
    birth_date = models.DateField(null=True, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True, max_length=2000)
    house = models.ForeignKey(House, null=True, blank=True, on_delete=models.SET_NULL)
    boarding_type = SingleChoiceField(PupilBoardingType, null=True, blank=True)
    year_group = models.ForeignKey(YearGroup, null=True, blank=True, on_delete=models.SET_NULL)
    # free_periods = ??? TODO: JSONField

    def get_display_name(self):
        if self.display_name:
            return self.display_name
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"


class PrivacySetting(IntFlag):
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

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"


class FrequencySetting(IntFlag):
    IMMEDIATE = auto()
    DAY = auto()
    THREE_DAYS = auto()
    WEEK = auto()
    NEVER = auto()


class GenderFilter(IntFlag):
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
    subjects_match = models.FloatField(default=0.0)  # TODO: set default
    interests_match = models.FloatField(default=0.0)  # TODO: set default

    def __repr__(self):
        return f"<{self.__class__.__name__} of {self.user}>"
