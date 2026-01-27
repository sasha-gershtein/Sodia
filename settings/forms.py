from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from api.errors import FormResponseUserError
from .models import UserAccountSettings, UserPrivacySettings, UserNotificationSettings, UserChallengesSettings
from settings.models import UserAccountSettings


class AccountForm(forms.ModelForm):
    class Meta:
        model = UserAccountSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "account")
        super().__init__(*args, **kwargs)


class PrivacyForm(forms.ModelForm):
    class Meta:
        model = UserPrivacySettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "privacy")
        super().__init__(*args, **kwargs)


class NotificationsForm(forms.ModelForm):
    class Meta:
        model = UserNotificationSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "notifications")
        super().__init__(*args, **kwargs)


class ChallengesForm(forms.ModelForm):
    class Meta:
        model = UserChallengesSettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "challenges")
        super().__init__(*args, **kwargs)
