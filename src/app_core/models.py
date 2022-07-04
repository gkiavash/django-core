from django.db import models
from model_utils.models import TimeStampedModel


from . import mixins as core_mixins


class Resource(
    core_mixins.UuidMixin,
    core_mixins.ErrorMessageMixin,
    core_mixins.NameMixin,
    # core_mixins.DescribableMixin,
    core_mixins.BackendModelMixin,
    TimeStampedModel,
    core_mixins.RuntimeStateMixin,
    core_mixins.StateMixin
):
    class Meta:
        abstract = True

    def get_backend(self):
        raise NotImplementedError

    @classmethod
    def get_url_name(cls):
        """ This name will be used by generic relationships to membership model for URL creation """
        return '{}-{}'.format(cls._meta.app_label, cls.__name__.lower())

    def get_log_fields(self):
        return ('uuid', 'name')
