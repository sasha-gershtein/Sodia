"""This file defines a form subclass used in model forms submitted via API"""

from django import forms
from django.db import models


class UpdateForm(forms.ModelForm):
    """Subclass of ModelForm defining get_updated_form() method"""

    @classmethod
    def get_updated_form(cls, data, instance: models.Model):
        """get a form instantiated with data merged from data and instance fields values"""
        initial_form = cls(instance=instance)
        merged_data = {
            initial_form.add_prefix(name): value for name, value in initial_form.initial.items()
        }
        merged_data.update(data)
        return cls(merged_data, instance=instance)
