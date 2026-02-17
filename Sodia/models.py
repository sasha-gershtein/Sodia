"""
This module defines models and model fields not specific to any app in the project.
It extends model field types built into Django:
* FloatField can now be passed min_value and max_value, which are reflected on form fields generated from model fields
* CharField can now be passed min_length and pattern (RegEx validation), which  are reflected on the form fields
* SingleChoiceField and MultipleChoiceField accept an enum type and implement choice model fields
"""

from enum import IntFlag, IntEnum
from functools import reduce
from collections.abc import Sequence, Mapping

from django.core.validators import MinValueValidator, MaxValueValidator, MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models
from django import forms


class FloatField(models.FloatField):
    def __init__(self, *args, min_value=None, max_value=None, _initialized=False, **kwargs):
        self.min_value = min_value
        self.max_value = max_value

        if not _initialized:
            validators = list(kwargs.pop("validators", []))
            if min_value is not None:
                validators.append(MinValueValidator(min_value))
            if max_value is not None:
                validators.append(MaxValueValidator(max_value))
            kwargs["validators"] = validators

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.min_value is not None:
            kwargs["min_value"] = self.min_value
        if self.max_value is not None:
            kwargs["max_value"] = self.max_value
        kwargs["_initialized"] = True
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            "min_value": self.min_value,
            "max_value": self.max_value,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class CharField(models.CharField):
    def __init__(self, *args, min_length: int | None = None,
                 pattern: str | Sequence | Mapping | RegexValidator | None = None,
                 _initialized=False, **kwargs):
        self.min_length = min_length
        self.pattern: str | None = pattern if isinstance(pattern, str) else None

        if not _initialized:
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
        kwargs["_initialized"] = True
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {
            "min_length": self.min_length,
        }
        defaults.update(kwargs)
        field = super().formfield(**defaults)
        if self.pattern is not None:
            field.widget.attrs["pattern"] = self.pattern.strip("^$")
        return field


class SingleChoiceField(models.IntegerField):
    def __init__(self, enum_class: type[IntEnum | IntFlag], *args, **kwargs):
        self.enum_class = enum_class
        defaults = {
            "choices": [
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
        if not value:
            return self.enum_class(0)
        return self.enum_class(int(value))


class IntFlagList(list):
    def __init__(self, *args, enum_class: type[IntFlag] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_class = enum_class

    def enum(self, enum_class: type[IntFlag] | None = None):
        enum_class = enum_class or self.enum_class
        if not self:
            assert enum_class is not None, "enum_class must be defined"
            return enum_class(0)
        return reduce(lambda x, y: x | y, self)

    def __int__(self):
        return int(self.enum())


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
            (flag, flag.name.replace("_", " ").capitalize()) for flag in enum_class
        ]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_class"] = self.enum_class
        return name, path, args, kwargs

    def from_db_value(self, value, _expression, _connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None or isinstance(value, IntFlagList):
            return value
        if not value:
            return IntFlagList([], enum_class=self.enum_class)
        if isinstance(value, Sequence):
            return IntFlagList([self.enum_class(int(flag)) for flag in value], enum_class=self.enum_class)
        return IntFlagList(
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
            raise ValidationError(f"Invalid flag value")

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.TypedMultipleChoiceField,
            "choices": self.flags,
            "coerce": int,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def clean(self, value, model_instance):
        value = self.to_python(value)
        self.validate(value, model_instance)
        return value
