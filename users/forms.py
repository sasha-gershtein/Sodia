from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import User, UserLoginDetails
from settings.models import UserAccountSettings


class LoginForm(forms.Form):
    identifier = forms.CharField(label="Username or email", max_length=254)
    password = forms.CharField(widget=forms.PasswordInput, max_length=100)

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
            raise ValidationError("Invalid username/email or password.", code="invalid_credentials")

        if not user.login_details.password.verify(password):
            raise ValidationError("Invalid username/email or password.", code="invalid_credentials")

        cleaned_data["user"] = user
        return cleaned_data