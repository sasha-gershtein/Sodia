from django.db import models

class IntFlagField(models.IntegerField):
    def __init__(self, enum_class, exclusive_choices=False, *args, **kwargs):
        self.enum_class = enum_class
        choices = []
        for e in enum_class:
            self.__setattr__(e.name, e.value)
            choices.append((e.value, e.name.lower()))
        if exclusive_choices:
            kwargs.setdefault('choices', choices)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs['enum_class'] = self.enum_class
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.enum_class(value)

    def to_python(self, value):
        if isinstance(value, self.enum_class) or value is None:
            return value
        return self.enum_class(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        return int(value)
