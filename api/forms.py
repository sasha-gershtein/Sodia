from django import forms
from django.db import models


class UpdateForm(forms.ModelForm):
    @classmethod
    def get_updated_form(cls, data, instance: models.Model):
        initial_form = cls(instance=instance)
        merged_data = {
            initial_form.add_prefix(name): value for name, value in initial_form.initial.items()
        }
        merged_data.update(data)
        return cls(merged_data, instance=instance)
