#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from itertools import groupby

from wtforms import SelectField, SelectMultipleField


class LazySelectField(SelectField):
    def __init__(self, label=None, validators=None, coerce=str, choices=None, choices_attrs=None, **kwargs):
        self._choices = choices
        self._choices_attrs = choices_attrs
        super().__init__(label, validators, coerce=coerce, choices=None, **kwargs)

    @property
    def choices(self):
        result = self._choices()
        a = self._choices_attrs
        if a is not None:
            result = [(getattr(x, a[0]), getattr(x, a[1])) for x in result]
        return result

    @choices.setter
    def choices(self, value):
        if value is not None:
            raise ValueError('Cannot set choices for lazy field')

    @property
    def raw_choices(self):
        return self._choices()


class LazySelectMultipleField(SelectMultipleField):
    def __init__(self, label=None, validators=None, coerce=str, choices=None, choices_attrs=None, **kwargs):
        self._choices = choices
        self._choices_attrs = choices_attrs
        super().__init__(label, validators, coerce=coerce, choices=None, **kwargs)

    @property
    def choices(self):
        result = self._choices()
        a = self._choices_attrs
        if a is not None:
            result = [(getattr(x, a[0]), getattr(x, a[1])) for x in result]
        return result

    @choices.setter
    def choices(self, value):
        if value is not None:
            raise ValueError('Cannot set choices for lazy field')

    @property
    def raw_choices(self):
        return self._choices()


class GroupedModelChoiceIterator(object):
    def __init__(self, group_by_field, choices, choices_attrs=None):
        self.group_by_field = group_by_field
        self.choices = choices
        self.choices_attrs = choices_attrs

    def __iter__(self):
        a = self.choices_attrs
        for group, choices in groupby(self.choices, lambda row: getattr(row, self.group_by_field)):
            if a is not None:
                choices = [(getattr(row, a[0]), getattr(row, a[1])) for row in choices]
            yield (group, choices)


class GroupedModelChoiceField(LazySelectMultipleField):
    def __init__(self, label=None, validators=None, coerce=str, choices=None, choices_attrs=None, group_by_field=None, group_label=None, **kwargs):
        """
        group_by_field is the name of a field on the model
        group_label is a function to return a label for each choice group
        """
        super().__init__(label, validators, coerce=coerce, choices=choices, choices_attrs=choices_attrs, **kwargs)
        self.group_by_field = group_by_field
        if group_label is None:
            self.group_label = lambda group: group
        else:
            self.group_label = group_label

    @property
    def choices_groups(self):
        return GroupedModelChoiceIterator(self.group_by_field, self.raw_choices, self._choices_attrs)

    @property
    def raw_choices_groups(self):
        return GroupedModelChoiceIterator(self.group_by_field, self.raw_choices, None)
