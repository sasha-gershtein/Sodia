from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from api.errors import FormResponseUserError
from .models import UserLoginDetails
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

        if not identifier or not password:
            return cleaned_data

        is_email = True
        try:
            validate_email(identifier)
        except ValidationError:
            is_email = False

        try:
            if is_email:
                user = UserLoginDetails.objects.get(email__iexact=identifier).user
            else:
                user = UserAccountSettings.objects.get(username__iexact=identifier).user
        except (UserLoginDetails.DoesNotExist, UserAccountSettings.DoesNotExist):
            raise FormResponseUserError("Incorrect username or password. Please check your details and try again",
                                        code="invalid_credentials")

        if not user.login_details.password.verify(password):
            raise FormResponseUserError("Incorrect username or password. Please check your details and try again",
                                        code="invalid_credentials")

        cleaned_data["user"] = user
        return cleaned_data

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
        password_confirm = cleaned_data.get("password_confirm")

        if UserLoginDetails.objects.filter(email=email).exists():
            raise FormResponseUserError(
                "An account with this email address already exists. You can try to sign in instead",
                code="email_exists")

        if password != password_confirm:
            raise ValidationError("Passwords don't match. Please check and try again",
                                  code="password_mismatch")

        cleaned_data.pop("password_confirm")
        return cleaned_data
