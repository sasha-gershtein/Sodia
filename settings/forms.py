from api.forms import UpdateForm

from .models import UserAccountSettings, UserPrivacySettings, UserNotificationSettings, UserChallengesSettings


class AccountForm(UpdateForm):
    class Meta:
        model = UserAccountSettings
        fields = ["username", "first_name", "last_name", "display_name"]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "account")
        super().__init__(*args, **kwargs)


class PrivacyForm(UpdateForm):
    class Meta:
        model = UserPrivacySettings
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "privacy")
        super().__init__(*args, **kwargs)


class NotificationsForm(UpdateForm):
    class Meta:
        model = UserNotificationSettings
        fields = "__all__"

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
