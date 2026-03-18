"""
This module defines models and model fields not specific to any one app in the project.
It extends model field types built into Django:
* FloatField can be passed min_value and max_value, which are reflected on form fields generated from model fields
* DateField can be passed min_value and max_value, which are reflected on form fields; DateField widgets use type="date"
* CharField can be passed min_length and pattern (RegEx validation), which  are reflected on the form fields
* SingleChoiceField and MultipleChoiceField accept an enum type and implement choice model fields
"""

from enum import IntFlag, IntEnum, Enum
from functools import reduce
from collections.abc import Sequence, Mapping

from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django import forms


class MinMaxMixin:
    """Mixin class for common behaviours of FloatField and DateField (min and max values validation)"""

    def __init__(self, *args, min_value=None, max_value=None, _initialized=False, **kwargs):
        self.min_value = min_value
        self.max_value = max_value

        if not _initialized:
            # if validators are not already attached, add min and max value validators
            validators = list(kwargs.pop("validators", []))
            if min_value is not None:
                validators.append(MinValueValidator(min_value))
            if max_value is not None:
                validators.append(MaxValueValidator(max_value))
            kwargs["validators"] = validators

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        """Define parameters to be passed to instantiate the Field class when a row is read from db"""
        # when this mixin is used, it will have a Field class in MRO, but PyCharm doesn't know that, so supress warning:
        # noinspection PyUnresolvedReferences
        name, path, args, kwargs = super().deconstruct()
        if self.min_value is not None:
            kwargs["min_value"] = self.min_value
        if self.max_value is not None:
            kwargs["max_value"] = self.max_value
        kwargs["_initialized"] = True  # validators are already attached, no need to reattach
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }
        defaults.update(kwargs)
        # if value is None, do not pass it to allow resetting default min_value or max_value (used by DateField)
        # when this mixin is used, it will have a Field class in MRO, but PyCharm doesn't know that, so supress warning:
        # noinspection PyUnresolvedReferences
        return super().formfield(**{key: value for key, value in defaults.items() if value is not None})


class FloatField(MinMaxMixin, models.FloatField):
    """FloatField that allows min and max values to be passed to its constructor explicitly.
    Model field and form field validators are added according to the specified constraints."""
    pass


class DateField(MinMaxMixin, models.DateField):
    """DateField that allows min and max values to be passed to its constructor explicitly.
    Model field and form field validators are added according to the specified constraints."""

    def formfield(self, **kwargs):
        attrs = {
            "type": "date",  # force widget to be an <input type="date">, not text (default)
        }
        # manually add <input> attributes for min and max values
        # because DateField.formfield() does not accept min_value and max_value
        min_value = self.min_value() if callable(self.min_value) else self.min_value
        if min_value is not None:
            attrs["min"] = min_value
        max_value = self.max_value() if callable(self.max_value) else self.max_value
        if max_value is not None:
            attrs["max"] = max_value
        defaults = {
            "min_value": None,  # explicitly remove the parameters that would be passed by MinMaxMixin.formfield()
            "max_value": None,
            "widget": forms.DateInput(attrs=attrs),
        }
        defaults.update(kwargs)
        field = super().formfield(**defaults)
        return field


class CharField(models.CharField):
    """CharField that allows min_length value and RegEx pattern to be passed to its constructor explicitly.
    Model field and form field validators are added according to the specified constraints."""

    def __init__(self, *args, min_length: int | None = None,
                 pattern: str | Sequence | Mapping | RegexValidator | None = None,
                 _initialized=False, **kwargs):
        self.min_length = min_length
        self.pattern: str | None = pattern if isinstance(pattern, str) else None

        if not _initialized:
            # if validators are not already attached, add min_length and RegEx validators
            validators = list(kwargs.pop("validators", []))
            if min_length is not None:
                validators.append(MinLengthValidator(min_length))
            if pattern is not None:
                if isinstance(pattern, str):
                    validators.append(RegexValidator(pattern))
                elif isinstance(pattern, Sequence):
                    validators.append(RegexValidator(*pattern))
                elif isinstance(pattern, Mapping):
                    validators.append(RegexValidator(**pattern))
                elif isinstance(pattern, RegexValidator):
                    validators.append(pattern)
                self.pattern = validators[-1].regex.pattern
            kwargs["validators"] = validators

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.min_length is not None:
            kwargs["min_length"] = self.min_length
        if self.pattern is not None:
            kwargs["pattern"] = self.pattern
        kwargs["_initialized"] = True  # validators are already attached, no need to reattach
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            "min_length": self.min_length,
        }
        defaults.update(kwargs)
        field = super().formfield(**defaults)
        if self.pattern is not None:
            field.widget.attrs["pattern"] = self.pattern.strip("^$")  # do not use anchors, html adds them by default
        return field


class JsonEnumMixin(Enum):
    """Mixin to add the .get_json_value() method for json serialization to enums."""

    def get_json_value(self):
        """Return a JSON serializable dictionary"""
        return {
            "id": self.value,
            "name": self.name,
        }


class SingleChoiceField(models.IntegerField):
    """IntegerField takes an enum of choice values and stores an integer in the database"""

    def __init__(self, enum_class: type[IntEnum | IntFlag], *args, **kwargs):
        self.enum_class = enum_class
        defaults = {
            "choices": [
                # enum entries names like "ENUM_ENTRY_NAME" turn to "Enum entry name"
                (int(choice), choice.name.replace("_", " ").capitalize()) for choice in enum_class
            ],
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_class"] = self.enum_class
        return name, path, args, kwargs

    def from_db_value(self, value, _expression, _connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return None
        return self.enum_class(int(value))


class IntFlagList(list):
    """List of selected options (flags) that is JSON serializable
    and gives access to an IntFlag object through self.enum()"""

    def __init__(self, *args, enum_class: type[IntFlag] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = enum_class

    def enum(self, enum_class: type[IntFlag] | None = None):
        """Return an IntFlag object which is the binary OR of the list entries"""
        enum_class = enum_class or self.enum_class
        # enum class is inferred from data (if not empty)
        # or can be explicitly specified by passing to a constructor or this method as a parameter
        if not self:
            # raise an error if impossible to infer enum class
            assert enum_class is not None, "enum_class must be defined"
            return enum_class(0)
        return reduce(lambda x, y: x | y, self)

    def __int__(self):
        return int(self.enum())

    def get_json_value(self):
        """Return a JSON serializable dictionary"""
        return [
            {
                "id": flag.value,
                "name": flag.name,
            } for flag in self
        ]


class TypedMultipleChoiceFormField(forms.TypedMultipleChoiceField):
    """A formfield for model field MultipleChoiceField
    which returns an instance of IntFlagList and not list from .clean()"""

    def clean(self, *args, **kwargs):
        return IntFlagList(super().clean(*args, **kwargs))


class MultipleChoiceField(models.IntegerField):
    """Django does not implement models.MultipleChoiceField,
    integration with forms.TypedMultipleChoiceField requires .to_python() to return a list of selected choices
    IntegerField expects .to_python() to return an integer for validation
    I want .to_python() to be of the enum type
    ->  MultipleChoiceField.to_python() returns a list-inherited object which defines .enum() and int()
        .clean(), which is used for validation, does not call super().clean() to avoid broken default validation"""

    def __init__(self, enum_class: type[IntFlag], *args, **kwargs):
        self.enum_class = enum_class
        self.flags: list[tuple[int, str]] = [
            # enum entries names like "ENUM_ENTRY_NAME" turn to "Enum entry name"
            (flag, flag.name.replace("_", " ").capitalize()) for flag in enum_class
        ]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_class"] = self.enum_class
        return name, path, args, kwargs

    def from_db_value(self, value, _expression, _connection):
        return self.to_python(value)

    def to_python(self, value) -> IntFlagList | None:
        if value is None or isinstance(value, IntFlagList):
            # return None if None, and value if value is already IntFlagList
            return value
        if not value:
            # value isn't None but is 0 or []
            return IntFlagList([], enum_class=self.enum_class)
        if isinstance(value, Sequence) and not isinstance(value, str):
            # value is a list (or other sequence excluding str), but not IntFlagList
            return IntFlagList([self.enum_class(int(flag)) for flag in value], enum_class=self.enum_class)
        # value is a string or an integer of an IntFlag object's value
        return IntFlagList(
            # include flag if flag in value (value & flag != 0)
            [self.enum_class(flag) for flag, name in self.flags if int(value) & flag],
            enum_class=self.enum_class
        )

    def get_prep_value(self, value):
        if value is None:
            return None
        return int(self.to_python(value))

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not 0 <= self.get_prep_value(value) < self.flags[-1][0] << 1:
            # if not a valid IntFlag value, raise a ValidationError
            raise ValidationError(f"Invalid flag value")

    def formfield(self, **kwargs):
        defaults = {
            "form_class": TypedMultipleChoiceFormField,
            "choices": self.flags,  # restrict form field's choices, but not model field's
            "coerce": lambda choice: self.enum_class(int(choice)),
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def clean(self, value, model_instance):
        value = self.to_python(value)
        self.validate(value, model_instance)
        return value
