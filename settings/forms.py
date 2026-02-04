from django import forms

from api.forms import UpdateForm

from .models import UserAccountSettings, UserPrivacySettings, UserNotificationsSettings, UserChallengesSettings


class AccountForm(UpdateForm):
    class Meta:
        model = UserAccountSettings
        fields = [
            "username",
            "first_name",
            "last_name",
            "display_name",
            "is_full_name_hidden",
            "gender",
            "birth_date",
            "country",
            "description",
            "house",
            "boarding_type",
            "year_group",
        ]
        widgets = {
            "birth_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "account")
        super().__init__(*args, **kwargs)


class PrivacyForm(UpdateForm):
    class Meta:
        model = UserPrivacySettings
        fields = [
            "full_name",
            "profile_picture",
            "birthday",
            "free_periods",
            "interests",
            "description",
            "friends",
            "message"
        ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "privacy")
        super().__init__(*args, **kwargs)


class NotificationsForm(UpdateForm):
    class Meta:
        model = UserNotificationsSettings
        fields = [
            "unread_messages",
            "challenges_updates",
            "new_friend_requests",
            "accepted_friend_requests",
            "sodia_button_updates",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "notifications")
        super().__init__(*args, **kwargs)


class ChallengesForm(UpdateForm):
    class Meta:
        model = UserChallengesSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "challenges")
        super().__init__(*args, **kwargs)
