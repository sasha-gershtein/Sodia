"""this file defines forms related to app "users", including all input validation checks"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from api.errors import FormResponseUserError
from .models import User, UserLoginDetails


class LoginForm(forms.Form):
    """Form for user login API requests validation"""
    # username or email can be used for the identifier
    identifier = forms.CharField(label="Username or email", min_length=2, max_length=254,  # maximum email length = 254
                                 widget=forms.TextInput(attrs={"placeholder": "john.doe"}))
    password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # always use "login-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "login")
        super().__init__(*args, **kwargs)

    def clean(self):
        """validate input, identify a user and verify password"""
        cleaned_data = super().clean()  # default validation
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier is None or password is None:
            # if fields are missing, errors are already added by parent class, so stop validation
            return

        try:
            validate_email(identifier)  # check if identifier is an email address
        except ValidationError:
            # if not email address, assume it is a username
            # account does not to be activated to log into it
            user = User.objects.get_user_by_username(identifier, only_activated=False)
        else:
            # identifier is an email address
            # account does not to be activated to log into it
            user = User.objects.get_user_by_email(identifier, only_activated=False)

        if user is None or not user.login_details.password.verify(password):
            # user not fount or password didn't match
            self.add_error(None,
                           FormResponseUserError(  # custom error for API validation (subclass of ValidationError)
                               "Incorrect username or password. Please check your details and try again",
                               code="invalid_credentials")
                           )
            return

        # validation successful, record the matched user
        cleaned_data["user"] = user


class RegistrationForm(forms.Form):
    """Form for user registration API requests validation"""
    first_name = forms.CharField(min_length=2, max_length=50,
                                 widget=forms.TextInput(attrs={"placeholder": "John"}))
    last_name = forms.CharField(min_length=2, max_length=50,
                                widget=forms.TextInput(attrs={"placeholder": "Doe"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "john.doe2019@epsomcollege.org.uk"}))
    password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    password_confirm = forms.CharField(label="Confirm password", min_length=4, max_length=100,
                                       widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        # always use "registration-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "registration")
        super().__init__(*args, **kwargs)

    def clean(self):
        """validate input, ensure the user does not already exist"""
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.pop("password_confirm", None)  # remove password_confirm from cleaned_data

        if email is None or password is None or password_confirm is None:
            # if fields are missing, errors are already added by parent class, so stop validation
            return

        # check if user with this email already exists
        if UserLoginDetails.objects.get_user_by_email(email, only_activated=False) is not None:
            # add an error, but do not stop validation (might add another error about passwords' match)
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
    """Form for change password API requests validation"""
    # user is inferred from request's session authentication
    old_password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    new_password = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)
    new_password_confirm = forms.CharField(min_length=4, max_length=100, widget=forms.PasswordInput)

    def __init__(self, *args, user: User | None = None, **kwargs):
        # always use "change-password-..." as a prefix for html ids, unless overridden explicitly
        kwargs.setdefault("prefix", "change-password")
        super().__init__(*args, **kwargs)
        self.user = user  # set user from request's session authentication

    def clean(self):
        """validate input, verify old password"""
        cleaned_data = super().clean()
        old_password = cleaned_data.get("old_password")
        new_password = cleaned_data.get("new_password")
        # remove new_password_confirm from cleaned_data
        new_password_confirm = cleaned_data.pop("new_password_confirm", None)

        # a user has to be specified on validation, but may be None at template rendering
        assert self.user is not None, "ChangePasswordForm.user cannot be None on validation"

        if old_password is None or new_password is None or new_password_confirm is None:
            # if fields are missing, errors are already added by parent class, so stop validation
            return

        if not self.user.login_details.password.verify(old_password):
            # old password is incorrect
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


class SearchForm(forms.Form):
    """form for user search API requests validation (parsing and max_length restriction)"""
    query = forms.CharField(max_length=250, label="", widget=forms.TextInput(attrs={"placeholder": "Search users..."}))
