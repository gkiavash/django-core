import uuid

from model_utils import FieldTracker
from model_utils.models import TimeStampedModel
from django_fsm import FSMIntegerField, transition
from django.apps import apps
from django.conf import settings
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import JSONField
from django.utils.encoding import smart_text
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from rest_framework.routers import DefaultRouter


class StringUUID(uuid.UUID):
    """
    Default UUID class __str__ method returns hyphenated string.
    This class returns non-hyphenated string.
    """

    def __unicode__(self):
        return str(str(self))

    def __str__(self):
        return self.hex

    def __len__(self):
        return len(self.__unicode__())


class UUIDField(models.UUIDField):
    """
    This class implements backward-compatible non-hyphenated rendering of UUID values.
    Default field parameters are not exposed in migrations.
    """

    def __init__(self, **kwargs):
        kwargs["default"] = lambda: StringUUID(uuid.uuid4().hex)
        kwargs["editable"] = False
        kwargs["unique"] = True
        super(UUIDField, self).__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(UUIDField, self).deconstruct()
        del kwargs["default"]
        del kwargs["editable"]
        del kwargs["unique"]
        return name, path, args, kwargs

    def _parse_uuid(self, value):
        if not value:
            return None
        try:
            return StringUUID(smart_text(value))
        except ValueError:
            return None

    def from_db_value(self, value, expression, connection, context=None):
        return self._parse_uuid(value)

    def to_python(self, value):
        return self._parse_uuid(value)


class UuidMixin(models.Model):
    """
    Mixin to identify models by UUID.
    """

    class Meta:
        abstract = True

    uuid = UUIDField()


class ErrorMessageMixin(models.Model):
    """
    Mixin to add a standardized "error_message" and "error_traceback" fields.
    """

    class Meta:
        abstract = True

    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)


class NameMixin(models.Model):
    """
    Mixin to add a standardized "name" field.
    """

    class Meta:
        abstract = True

    name = models.CharField(_("name"), max_length=150, null=True, blank=True)


class DescribableMixin(models.Model):
    """
    Mixin to add a standardized "description" field.
    """

    class Meta:
        abstract = True

    description = models.CharField(_("description"), max_length=2000, blank=True)


class ScopeMixin(models.Model):
    class Meta:
        abstract = True

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="+",
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    scope = GenericForeignKey("content_type", "object_id")


class UserDetailsMixin(models.Model):
    class Meta:
        abstract = True

    full_name = models.CharField(_("full name"), max_length=100, blank=True)
    native_name = models.CharField(_("native name"), max_length=100, blank=True)
    phone_number = models.CharField(_("phone number"), max_length=255, blank=True)
    organization = models.CharField(_("organization"), max_length=255, blank=True)
    job_title = models.CharField(_("job title"), max_length=40, blank=True)


class BackendModelMixin(models.Model):
    """
    Represents model that is connected to backend object.

    This model cannot be created or updated via admin, because we do not support queries to backend from admin interface.
    """
    class Meta:
        abstract = True

    backend_id = models.CharField(max_length=255, blank=True)

    @classmethod
    def get_backend_class(cls):
        raise NotImplementedError

    @classmethod
    def get_backend_fields(cls):
        return ('backend_id',)

    def get_backend(self, **kwargs):
        raise NotImplementedError


class BackendResourceMixin(
    UuidMixin,
    ErrorMessageMixin,
    NameMixin,
    DescribableMixin,
    BackendModelMixin,
    TimeStampedModel,
):

    """ Base resource class. Resource is a provisioned entity of a service,
    """

    class Meta:
        abstract = True

    @classmethod
    def get_url_name(cls):
        """ This name will be used by generic relationships to membership model for URL creation """
        return '{}-{}'.format(cls._meta.app_label, cls.__name__.lower())

    def get_log_fields(self):
        return ('uuid', 'name')


class RuntimeStateMixin(models.Model):
    """ Provide runtime_state field """

    class RuntimeStates:
        REQUESTED = "REQUESTED"
        IN_SERVICE = "IN_SERVICE"
        DECOMMISSIONED = "DECOMMISSIONED"

        CHOICES = (
            (REQUESTED, "REQUESTED"),
            (IN_SERVICE, "IN_SERVICE"),
            (DECOMMISSIONED, "DECOMMISSIONED"),
        )

    class Meta:
        abstract = True

    runtime_state = models.CharField(
        _("runtime state"),
        max_length=150,
        choices=RuntimeStates.CHOICES,
        default=RuntimeStates.REQUESTED,
        blank=True,
        null=True,
    )


class StateMixin(models.Model):
    class States:
        CREATION_SCHEDULED = 5
        CREATING = 6
        UPDATE_SCHEDULED = 1
        UPDATING = 2
        DELETION_SCHEDULED = 7
        DELETING = 8
        OK = 3
        ERRED = 4

        CHOICES = (
            (CREATION_SCHEDULED, 'Creation Scheduled'),
            (CREATING, 'Creating'),
            (UPDATE_SCHEDULED, 'Update Scheduled'),
            (UPDATING, 'Updating'),
            (DELETION_SCHEDULED, 'Deletion Scheduled'),
            (DELETING, 'Deleting'),
            (OK, 'OK'),
            (ERRED, 'Erred'),
        )

    class Meta:
        abstract = True

    state = FSMIntegerField(default=States.CREATION_SCHEDULED, choices=States.CHOICES,)

    @property
    def human_readable_state(self):
        return force_text(dict(self.States.CHOICES)[self.state])

    @transition(field=state, source='*', target=States.CREATING)
    def begin_creating(self):
        pass

    @transition(field=state, source='*', target=States.UPDATING)
    def begin_updating(self):
        pass

    @transition(field=state, source='*', target=States.DELETING)
    def begin_deleting(self):
        pass

    @transition(field=state, source='*', target=States.UPDATE_SCHEDULED)
    def schedule_updating(self):
        pass

    @transition(field=state, source='*', target=States.DELETION_SCHEDULED)
    def schedule_deleting(self):
        pass

    @transition(field=state, source='*', target=States.OK)
    def set_ok(self):
        pass

    @transition(field=state, source='*', target=States.ERRED)
    def set_erred(self):
        pass

    @transition(field=state, source=States.ERRED, target=States.OK)
    def recover(self):
        pass


    @classmethod
    def get_index_by_str(cls, state_str):
        return list(dict(cls.States.CHOICES).values()).index(str(state_str))


class SimpleStateMixin(models.Model):
    """Provide simple state field"""

    class Meta:
        abstract = True

    class States:
        AVAILABLE = "AVAILABLE"
        NOT_AVAILABLE = "NOT_AVAILABLE"

        STATES_CHOICES = (
            (AVAILABLE, "AVAILABLE"),
            (NOT_AVAILABLE, "NOT_AVAILABLE"),
        )

    state = models.CharField(
        _("state"),
        max_length=150,
        choices=States,
        default=States.AVAILABLE,
        blank=True,
        null=True,
    )


# todo: can we create a mixin to do versioned models that have a foreign key to another model
# This could also be a generic model?

# class VersionedDeclarationMixin(models.Model):
#     '''
#     Creates a model with a declaration JSON field and a version number. Overrides save to increment the version
#     '''
#
#     description = JSONField(default=dict)
#     version = models.PositiveIntegerField(default=1)
#
#     def get_fk_field(self):
#         """
#         Returns a list of validator callables.
#         """
#         # Used by the lazily-evaluated `validators` property.
#         meta = getattr(self, 'Meta', None)
#         unique_fk_field = getattr(meta, 'unique_fk_field', None)
#         return unique_fk_field if unique_fk_field else None
#
#     def save(self, *args, **kwargs):
#         '''
#         Overide save to increment version based on service_item relation
#         '''
#         version = cal_version(self.get_fk_field())
#         self.version = version
#         super(VersionedDeclarationMixin, self).save(*args, **kwargs)
#
#     def cal_version(self, fk_fieldname):
#         '''
#         Calculations the DeployedItem version number based on the foreign key
#         '''
#         fk = getattr(self, fk_fieldname, None)
#         present_version = self.objects.filter(fk_fieldname=fk).order_by('-version').values_list('version',
#                                                                                                         flat=True)
#         if present_version:
#             return present_version[0] + 1
#         else:
#             return 1
#
#     class Meta:
#         abstract = True
