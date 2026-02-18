from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from api.errors import FormResponseUserError
from .models import User, UserLoginDetails
from settings.models import UserAccountSettings


class LoginForm(forms.Form):
    identifier = forms.CharField(label="Username or email", min_length=4, max_length=254,
                                 widget=forms.TextInput(attrs={"placeholder": "john.doe"}))
    password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "login")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier is None or password is None:
            return cleaned_data

        try:
            validate_email(identifier)
        except ValidationError:
            user = User.objects.get_user_by_username(identifier, only_activated=False)
        else:
            user = User.objects.get_user_by_email(identifier, only_activated=False)

        if user is None or not user.login_details.password.verify(password):
            self.add_error(None,
                           FormResponseUserError(
                               "Incorrect username or password. Please check your details and try again",
                               code="invalid_credentials")
                           )
            return

        cleaned_data["user"] = user


class RegistrationForm(forms.Form):
    first_name = forms.CharField(min_length=2, max_length=50,
                                 widget=forms.TextInput(attrs={"placeholder": "John"}))
    last_name = forms.CharField(min_length=2, max_length=50,
                                widget=forms.TextInput(attrs={"placeholder": "Doe"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "john.doe@example.com"}))
    password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirm password", min_length=4, max_length=100,
                                       widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("prefix", "registration")
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.pop("password_confirm", None)

        if email is None or password is None or password_confirm is None:
            return

        if UserLoginDetails.objects.filter(email=email).exists():
            self.add_error(
                "email",
                FormResponseUserError(
                    "An account with this email address already exists. You can try to sign in instead",
                    code="email_exists"
                )
            )

        if password != password_confirm:
            self.add_error(
                "password",
                ValidationError("Passwords don't match. Please check and try again", code="password_mismatch")
            )


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    new_password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    new_password_confirm = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)

    def __init__(self, *args, user: User | None = None, **kwargs):
        kwargs.setdefault("prefix", "change-password")
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        new_password_confirm = cleaned_data.pop("new_password_confirm", None)

        assert self.user is not None, "ChangePasswordForm.user cannot be None on validation"

        if old_password is None or new_password is None or new_password_confirm is None:
            return

        if not self.user.login_details.password.verify(old_password):
            self.add_error(
                "old_password",
                FormResponseUserError("Incorrect password. Please check and try again", code="invalid_password")
            )

        if new_password != new_password_confirm:
            self.add_error("new_password_confirm", ValidationError(
                "Passwords don't match. Please check and try again",
                code="password_mismatch"
            ))
            return

        if old_password == new_password:
            self.add_error(
                None,
                FormResponseUserError("New password must be different from the old password", code="password_unchanged")
            )
