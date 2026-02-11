"""
This module defines models and model fields not specific to any app in the project.
It extends model field types built into Django:
* FloatField can now be passed min_value and max_value, which are reflected on form fields generated from model fields
* SingleChoiceField and MultipleChoiceField accept an enum type and implement choice model fields
  Django does not implement models.MultipleChoiceField,
  and the integration with forms.TypedMultipleChoiceField is not behaving very well,
  so the MultipleChoiceField class uses a hack (a custom int-like list of selected flags)
"""

from enum import IntFlag, IntEnum
from functools import reduce
from collections.abc import Sequence

from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django import forms


class FloatField(models.FloatField):
    def __init__(self, min_value=None, max_value=None, *args, **kwargs):
        self.min_value = min_value
        self.max_value = max_value
        validators = kwargs.setdefault("validators", [])
        if min_value is not None:
            validators.append(MinValueValidator(min_value))
        if max_value is not None:
            validators.append(MaxValueValidator(max_value))
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.min_value is not None:
            kwargs["min_value"] = self.min_value
        if self.max_value is not None:
            kwargs["max_value"] = self.max_value
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {'min_value': self.min_value, 'max_value': self.max_value}
        defaults.update(kwargs)
        return super().formfield(**defaults)


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

    def __lt__(self, other):
        if isinstance(other, int):
            return int(self) < other
        return super() < other

    def __gt__(self, other):
        if isinstance(other, int):
            return int(self) > other
        return super() > other

    def __eq__(self, other):
        if isinstance(other, int):
            return int(self) == other
        return super() == other


class MultipleChoiceField(models.IntegerField):
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
        if value is None:
            return None
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
