from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers, exceptions
from rest_framework.fields import empty
from django.utils.encoding import force_text

from . import mixins as core_mixins


class ResourceSerializer(serializers.HyperlinkedModelSerializer):
    state = serializers.SerializerMethodField(read_only=True, source='get_human_readable_state')
    # def get_fields(self):
    #     fields = super(ResourceSerializer, self).get_fields()
    #     fields += self.get_scope_fields()
    #     return fields

    def get_state(self, obj):
        return obj.human_readable_state

    def get_scope_fields(self):
        return ()

    class Meta:
        model = NotImplemented
        fields = (
            'id',
            'uuid',

            'error_message',
            # 'error_traceback',

            'name',

            'backend_id',

            'created',
            'modified',

            'runtime_state',
            'state'
        )
        read_only_fields = (
            'uuid',

            'error_message',
            # 'error_traceback',

            'name',

            'backend_id'
            
            'created',
            'modified',

            'runtime_state',
            'state'
        )

    @transaction.atomic
    def create(self, validated_data):
        instance = super(ResourceSerializer, self).create(validated_data)
        return instance

    def validate(self, attrs):
        return super(ResourceSerializer, self).validate(attrs)


@extend_schema_field(OpenApiTypes.BINARY,)
class CoreFileField(serializers.FileField):
    pass


class GenericSerializer(serializers.ModelSerializer):
    def __init__(self, instance=None, data=empty, **kwargs):
        setattr(
            self,
            "Meta",
            type(
                "Meta",
                (),
                {"model": kwargs.pop("model_"), "fields": kwargs.pop("fields_")},
            ),
        )
        super().__init__(instance=instance, data=data, **kwargs)


class StateField(serializers.CharField):
    model_ = core_mixins.StateMixin

    def to_representation(self, value):
        # to put in serializer
        # value is 1,2,3,...
        return force_text(dict(self.model_.States.CHOICES)[value])

    def to_internal_value(self, data):
        # to fill the object
        # data is "state_str e.g. COMPLETED"
        return list(dict(self.model_.States.CHOICES).values()).index(str(data))
