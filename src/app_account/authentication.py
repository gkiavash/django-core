from django.utils import timezone
from django.conf import settings
from rest_framework import authentication, exceptions
from rest_framework_api_key import permissions as api_key_permissions

from . import models as account_models


class ExpiringTokenAuthentication(authentication.TokenAuthentication):
    """Same as in DRF, but also handle Token expiration.

    An expired Token will be removed and a new Token with a different
    key is created that the User can obtain by logging in with his
    credentials.

    Raise AuthenticationFailed as needed, which translates
    to a 401 status code automatically.
    """

    def authenticate_credentials(self, key):
        user_, token = super().authenticate_credentials(key)
        if is_token_expired(token):
            raise exceptions.AuthenticationFailed("Token has expired")
        return user_, token


def is_token_expired(token):
    if (timezone.now() - token.created).seconds >= settings.TOKEN_EXPIRED_AFTER_SECONDS:
        token.delete()
        return True
    return False


class ApiKeyAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        key = api_key_permissions.KeyParser().get(request)
        if key is None:
            return None

        key = request.META["HTTP_AUTHORIZATION"].split()[1]
        api_key = account_models.AccountAPIKey.objects.get_from_key(key)

        return api_key.user, None
