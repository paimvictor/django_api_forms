import typing

from enum import Enum

from django.core.exceptions import ValidationError
from django.forms import Field

from django.utils.translation import gettext_lazy as _

from django_request_formatter.exceptions import RequestValidationError


class FieldList(Field):
    default_error_messages = {
        'not-list': _('This field have to be a list of objects!'),
    }

    def __init__(self, field, **kwargs):
        if not isinstance(field, Field):
            raise RuntimeError("Invalid Field type passed into FieldList!")

        self._field = field

        super().__init__(**kwargs)

    def to_python(self, value) -> typing.List:
        if not isinstance(value, list):
            raise ValidationError(self.error_messages['not_list'], code='not_list')

        result = []
        errors = []

        for item in value:
            if isinstance(self._field, Field):
                try:
                    self._field.clean(item)
                    result.append(self._field.to_python(item))
                except ValidationError as e:
                    errors.append(e)
            else:
                errors.append(
                    ValidationError(f"Invalid field_type {type(self._field)} in FieldList", code='type_mismatch'))

        if errors:
            raise ValidationError(errors)

        return result


class FormField(Field):
    def __init__(self, form: typing.Type, **kwargs):
        self._form = form

        super().__init__(**kwargs)

    @property
    def form(self):
        return self._form

    def to_python(self, value) -> dict:
        form = self._form(value)
        if form.is_valid():
            return form.cleaned_data
        else:
            raise RequestValidationError(form.errors)


class FormFieldList(FormField):
    default_error_messages = {
        'not_list': _('This field have to be a list of objects!')
    }

    def to_python(self, value):
        if not isinstance(value, list):
            raise ValidationError(self.error_messages['not_list'], code='not_list')

        result = []
        errors = []

        for item in value:
            form = self._form(item)
            if form.is_valid():
                result.append(form.cleaned_data)
            else:
                errors.append(form.errors)

        if errors:
            raise RequestValidationError(errors)

        return result


class EnumField(Field):
    default_error_messages = {
        'not_enum': _('This field have to be a subclass of enum.Enum')
    }

    def __init__(self, enum: typing.Type, **kwargs):
        if not issubclass(enum, Enum):
            raise RuntimeError("Invalid Field type passed into FieldList!")

        self.enum = enum

        super().__init__(**kwargs)

    def to_python(self, value) -> typing.Union[typing.Type[Enum], None]:
        if value is not None:
            try:
                return self.enum(value)
            except ValueError:
                raise ValidationError(f"Invalid enum value {value} passed to {type(self.enum)}")
        return None


class DictionaryField(Field):
    def __init__(self, value, **kwargs):
        if not isinstance(value, Field):
            raise RuntimeError("Invalid Field type passed into DictionaryField!")
        self._value = value
        super().__init__(**kwargs)

    def to_python(self, value) -> dict:
        if not isinstance(value, dict):
            raise ValidationError(f"Invalid value passed to DictionaryField (got {type(value)}, expected dict)")

        result = {}
        errors = {}

        for key, item in value.items():
            try:
                result[key] = self._value.clean(item)
            except ValidationError as e:
                errors[key] = e

        if errors:
            raise ValidationError(errors)

        return result
