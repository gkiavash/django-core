from django.shortcuts import render
from rest_framework import viewsets, authentication, permissions
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters

from rest_framework import response, status, viewsets, authentication, permissions

from rest_framework.exceptions import ValidationError
from braces.views import CsrfExemptMixin

from django.utils.translation import ugettext_lazy as _

from app_account import authentication as account_authentication
from . import (
    executors as core_executors,
    utils as core_utils,
    mixins as core_mixins,
    validators as core_validators,
    models as core_models,
)


def check_resource_backend_id(resource):
    if not resource.backend_id:
        raise ValidationError(_('Resource does not have backend ID.'))


class AsyncExecutor:
    async_executor = True


class CreateExecutorMixin(AsyncExecutor):
    create_executor = NotImplemented

    @core_utils.ensure_atomic_transaction
    def perform_create(self, serializer):
        instance = serializer.save()
        self.create_executor.execute(instance, is_async=self.async_executor)
        instance.refresh_from_db()


class UpdateExecutorMixin(AsyncExecutor):
    update_executor = NotImplemented

    def get_update_executor_kwargs(self, serializer):
        return {}

    @core_utils.ensure_atomic_transaction
    def perform_update(self, serializer):
        instance = self.get_object()
        # Save all instance fields before update.
        # To avoid additional DB queries - store foreign keys as ids.
        # Warning! M2M fields will be ignored.
        before_update_fields = {
            f: getattr(instance, f.attname) for f in instance._meta.fields
        }
        super(UpdateExecutorMixin, self).perform_update(serializer)
        instance.refresh_from_db()
        updated_fields = {
            f.name
            for f, v in before_update_fields.items()
            if v != getattr(instance, f.attname)
        }
        kwargs = self.get_update_executor_kwargs(serializer)

        self.update_executor.execute(
            instance,
            is_async=self.async_executor,
            updated_fields=updated_fields,
            **kwargs
        )
        serializer.instance.refresh_from_db()


class DeleteExecutorMixin(AsyncExecutor):
    delete_executor = NotImplemented

    @core_utils.ensure_atomic_transaction
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.delete_executor.execute(
            instance,
            is_async=self.async_executor,
            force=instance.state == core_mixins.StateMixin.States.ERRED,
        )
        return response.Response(
            {'detail': _('Deletion was scheduled.')}, status=status.HTTP_202_ACCEPTED
        )


class ExecutorMixin(CreateExecutorMixin, UpdateExecutorMixin, DeleteExecutorMixin):
    """ Execute create/update/delete operation with executor """

    pass


class ResourceViewSet(ExecutorMixin, viewsets.ModelViewSet):
    """ Basic view set for all resource view sets. """

    lookup_field = 'uuid'
    # authentication_classes = [authentication.SessionAuthentication, ]
    # authentication_classes = [authentication.TokenAuthentication, ]
    # permission_classes = [permissions.IsAuthenticated]
    # permission_classes = [HasAPIKey] if settings.API_KEY_ENABLE else []
    # filter_backends = DjangoFilterBackend
    update_validators = partial_update_validators = [
        core_validators.StateValidator(core_models.Resource.States.OK)
    ]
    destroy_validators = [
        core_validators.StateValidator(
            core_models.Resource.States.OK, core_models.Resource.States.ERRED
        )
    ]

    def get_serializer_class(self):
        default_serializer_class = super(ResourceViewSet, self).get_serializer_class()
        if self.action is None:
            return default_serializer_class
        return getattr(
            self, self.action + '_serializer_class', default_serializer_class
        )


@method_decorator(csrf_exempt, name='dispatch')
class CsrfExemptDRFLogin(CsrfExemptMixin, LoginView):
    pass


class AuthViewSetMixin:
    authentication_classes = (account_authentication.ExpiringTokenAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
