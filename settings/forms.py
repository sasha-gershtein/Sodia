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
            "gender",
            "birth_date",
            "country",
            "description",
            "house",
            "boarding_type",
            "year_group",
        ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "account")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        gender = cleaned_data.get("gender")
        house = cleaned_data.get("house")
        if username:
            cleaned_data["username"] = username.lower()
        if gender:
            cleaned_data["gender"] = gender.lower()
        if not house:
            cleaned_data["boarding_type"] = None
        return cleaned_data


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
        fields = [
            "frequency",
            "gender_filter",
            "subjects_match",
            "interests_match"
        ]
        widgets = {
            "gender_filter": forms.CheckboxSelectMultiple(attrs={"data-multiple": True}),
            "subjects_match": forms.NumberInput(attrs={"type": "range"}),
            "interests_match": forms.NumberInput(attrs={"type": "range"}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "challenges")
        super().__init__(*args, **kwargs)
