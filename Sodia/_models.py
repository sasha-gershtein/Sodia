from django.core.exceptions import ValidationError
from django.db import models
from django import forms


class MultipleChoiceField(models.IntegerField):
    def __init__(self, choices: list[str] | None = None, *args, flags: list[tuple[int, str]] | None = None, **kwargs):
        self.flags: list[tuple[int, str]] = flags if flags is not None else [
            (2 ** i, name) for i, name in enumerate(choices)
        ]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["flags"] = self.flags
        return name, path, args, kwargs

    def from_db_value(self, value, _expression, _connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return None
        if not value:
            return []
        if isinstance(value, list):
            return [int(flag) for flag in value]
        return [flag for flag, name in self.flags if int(value) & flag]

    def get_prep_value(self, value):
        if value is None:
            return None
        if not value:
            return 0
        if isinstance(value, list):
            return sum([int(flag) for flag in value])
        return int(value)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if not 0 <= self.get_prep_value(value) < self.flags[-1][0] << 1:
            raise ValidationError(f"Invalid flag value")

    def clean(self, value, model_instance):
        print(f"cleaning {value}")
        return self.to_python(value)

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.TypedMultipleChoiceField,
            "choices": self.flags,
            "coerce": int,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
