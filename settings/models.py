from enum import IntFlag, auto

from django.db import models

from Sodia.models import IntFlagField


# Create your models here.
class Country(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)


class HouseBoardingType(IntFlag):
    BOARDING = auto()
    DAY = auto()
    MIXED = auto()


class House(models.Model):
    name = models.CharField(max_length=20)
    boarding_type = IntFlagField(HouseBoardingType, exclusive_choices=True)


class PupilBoardingType(IntFlag):
    FULL = auto()
    WEEKLY = auto()
    DAY = auto()


class YearGroup(models.Model):
    year_group_number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)


class UserAccountSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name='account_settings',
                                primary_key=True)
    username = models.CharField(max_length=30, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(null=True, blank=True, max_length=100)
    is_full_name_hidden = models.BooleanField(default=False)
    # profile_picture = models.??? TODO
    gender = models.CharField(null=True, blank=True, max_length=30)
    birth_date = models.DateField(null=True, blank=True)
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(null=True, blank=True, max_length=2000)
    house = models.ForeignKey(House, null=True, blank=True, on_delete=models.SET_NULL)
    boarding_type = IntFlagField(PupilBoardingType, null=True, blank=True, exclusive_choices=True)
    year_group = models.ForeignKey(YearGroup, null=True, blank=True, on_delete=models.SET_NULL)
    # free_periods = ??? TODO: JSONField


class PrivacySetting(IntFlag):
    EVERYONE = auto()
    FRIENDS_ONLY = auto()
    NOBODY = auto()


class UserPrivacySettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="privacy_settings",
                                primary_key=True)
    full_name = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.EVERYONE)
    profile_picture = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.EVERYONE)
    birthday = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.EVERYONE)
    free_periods = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.FRIENDS_ONLY)
    interests = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.EVERYONE)
    description = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.EVERYONE)
    friends = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.FRIENDS_ONLY)
    message = IntFlagField(enum_class=PrivacySetting, exclusive_choices=True, default=PrivacySetting.FRIENDS_ONLY)


class UserNotificationSettings(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE, related_name="notification_settings",
                                primary_key=True)
    unread_messages = models.BooleanField(default=True)
    challenges_updates = models.BooleanField(default=True)
    new_friend_requests = models.BooleanField(default=True)
    accepted_friend_requests = models.BooleanField(default=True)
    sodia_button_updates = models.BooleanField(default=True)


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
    frequency = IntFlagField(enum_class=FrequencySetting, exclusive_choices=True, default=FrequencySetting.THREE_DAYS)
    # year_groups = TODO: JSONField
    gender_filter = IntFlagField(enum_class=GenderFilter, default=GenderFilter.ALL)
    subjects_match = models.FloatField(default=0.0)  # TODO: set default
    interests_match = models.FloatField(default=0.0)  # TODO: set default
