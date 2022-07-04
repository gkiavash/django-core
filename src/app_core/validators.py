from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


class IncorrectStateException(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('Cannot modify an object in its current state.')


class RuntimeStateException(Exception):
    pass


class StateValidator:
    def __init__(self, *valid_states):
        self.valid_states = valid_states

    def __call__(self, resource):
        if resource.state not in self.valid_states:
            states_names = dict(resource.States.CHOICES)
            valid_states_names = [
                str(states_names[state]) for state in self.valid_states
            ]
            raise IncorrectStateException(
                _('Valid states for operation: %s.') % ', '.join(valid_states_names)
            )


class RuntimeStateValidator(StateValidator):
    def __call__(self, resource):
        if resource.runtime_state not in self.valid_states:
            raise IncorrectStateException(
                _('Valid runtime states for operation: %s.')
                % ', '.join(self.valid_states)
            )


def state_validator_viewset(instance, valid_states):
    if instance.state not in valid_states:
        states_names = dict(instance.States.CHOICES)
        valid_states_names = [
            str(states_names[state]) for state in valid_states
        ]
        raise IncorrectStateException(
            _('Valid states for operation: %s.') % ', '.join(valid_states_names)
        )
