from collections.abc import Sequence

from enum import IntFlag as IntFlag

from django.db import models
from django import forms


def int_flag(is_multiple=False):
    def decorator(cls: type[IntFlag]):
        if is_multiple:
            def get_json_value(self: IntFlag) -> list[int]:
                return [int(flag) for flag in cls if flag in self]
        else:
            def get_json_value(self: IntFlag) -> int:
                return int(self)

        cls.is_multiple = is_multiple
        cls.get_json_value = get_json_value
        return cls

    return decorator


class IntFlagField(models.IntegerField):
    def __init__(self, enum_class, is_multiple=None, *args, **kwargs):
        self.enum_class = enum_class
        if is_multiple is None:
            is_multiple = getattr(enum_class, "is_multiple", None)
            assert is_multiple is not None, "enum_class must be decorated with @int_flag() if is_multiple is not passed"
        self.is_multiple = is_multiple
        self.flags: list[tuple[int, str]] = []
        for flag in enum_class:
            self.flags.append((int(flag), flag.name.replace("_", " ").capitalize()))
        if not self.is_multiple:
            kwargs.setdefault("choices", self.flags)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["enum_class"] = self.enum_class
        kwargs["is_multiple"] = self.is_multiple
        return name, path, args, kwargs

    def from_db_value(self, value, _expression, _connection) -> IntFlag | None:
        if self.enum_class.__name__ == "GenderFilter":
            ...
        if value is None:
            return value
        return (
            [flag for flag in self.enum_class if flag in self.enum_class(int(value))] if self.is_multiple
            else self.enum_class(int(value))
        )

    def to_python(self, value) -> IntFlag | None:
        if self.enum_class.__name__ == "GenderFilter":
            ...
        if isinstance(value, self.enum_class) or value is None:
            return value
        if not isinstance(value, str) and isinstance(value, Sequence):
            union = self.enum_class(0)
            print(value)
            for flag in value:
                union |= self.enum_class(int(flag))
            return union
        return (
            [flag for flag in self.enum_class if flag in self.enum_class(int(value))] if self.is_multiple
            else self.enum_class(int(value))
        )

    def get_prep_value(self, value):
        if value is None:
            return None
        return int(value)

    def formfield(self, **kwargs):
        if not self.is_multiple:
            widget = forms.Select(choices=self.flags)
        else:
            widget = forms.SelectMultiple(choices=self.flags)
        defaults = {
            "widget": widget,
        }
        if self.is_multiple:
            defaults.update({
                "form_class": forms.TypedMultipleChoiceField,
                "choices": self.flags,
                "coerce": lambda x: (print(f"coerce({x})"), self.to_python(x))[1],
            })
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def clean(self, value, model_instance):
        print(f"cleaning {value}: {repr(self.to_python(value))}")
        return self.to_python(value)
