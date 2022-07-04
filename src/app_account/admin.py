from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from rest_framework_api_key.admin import APIKeyModelAdmin

from . import models as account_models


class TeamAdmin(admin.ModelAdmin):
    pass


class MembershipAdmin(admin.ModelAdmin):
    pass


class InvitationAdmin(admin.ModelAdmin):
    pass


class AccountAPIKeyModelAdmin(APIKeyModelAdmin):
    pass


admin.site.register(account_models.Team, TeamAdmin)
admin.site.register(account_models.Membership, MembershipAdmin)
admin.site.register(account_models.Invitation, InvitationAdmin)
admin.site.register(account_models.User, UserAdmin)
admin.site.register(account_models.AccountAPIKey, AccountAPIKeyModelAdmin)
