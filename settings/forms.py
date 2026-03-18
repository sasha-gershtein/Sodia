"""This file defines settings forms, including all input validation checks"""

from django import forms

from api.forms import UpdateForm

from .models import UserAccountSettings, UserPrivacySettings, UserNotificationsSettings, UserChallengesSettings


class AccountForm(UpdateForm):
    """account settings form"""

    class Meta:
        model = UserAccountSettings  # AccountFrom form updates UserAccountSettings model
        fields = [  # list of fields included in the form
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
        # always use "account-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "account")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        gender = cleaned_data.get("gender")
        house = cleaned_data.get("house")
        if username:
            cleaned_data["username"] = username.lower()  # convert username to lowercase
        if gender:
            cleaned_data["gender"] = gender.lower()  # convert gender to lowercase
        if not house:
            cleaned_data["boarding_type"] = None  # boarding type cannot be defined if house is not defined
        return cleaned_data


class PrivacyForm(UpdateForm):
    """privacy settings form"""

    class Meta:
        model = UserPrivacySettings  # PrivacyForm form updates UserPrivacySettings model
        fields = [  # list of fields included in the form
            "full_name",
            "profile_picture",
            "birthday",
            "free_periods",
            "interests",
            "description",
            "friends",
            "message",
        ]

    def __init__(self, *args, **kwargs):
        # always use "privacy-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "privacy")
        super().__init__(*args, **kwargs)


class NotificationsForm(UpdateForm):
    """notification settings form"""

    class Meta:
        model = UserNotificationsSettings  # NotificationsForm form updates UserNotificationsSettings model
        fields = [  # list of fields included in the form
            "unread_messages",
            "challenges_updates",
            "new_friend_requests",
            "accepted_friend_requests",
            "sodia_button_updates",
        ]

    def __init__(self, *args, **kwargs):
        # always use "notifications-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "notifications")
        super().__init__(*args, **kwargs)


class ChallengesForm(UpdateForm):
    """challenges settings form"""

    class Meta:
        model = UserChallengesSettings  # ChallengesForm form updates UserChallengesSettings model
        fields = [  # list of fields included in the form
            "frequency",
            "gender_filter",
            "subjects_match",
            "interests_match"
        ]
        widgets = {
            # use checkboxes for gender filter (not <select multiple>)
            "gender_filter": forms.CheckboxSelectMultiple(attrs={"data-multiple": True}),
            "subjects_match": forms.NumberInput(attrs={"type": "range"}),  # use type="range", not "number"
            "interests_match": forms.NumberInput(attrs={"type": "range"}),  # use type="range", not "number"
        }

    def __init__(self, *args, **kwargs):
        # always use "challenges-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "challenges")
        super().__init__(*args, **kwargs)
