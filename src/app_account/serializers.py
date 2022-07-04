from rest_framework import serializers, exceptions, validators
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.reverse import reverse

from . import (
    models as account_models,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    teams = serializers.SerializerMethodField()

    def get_teams(self, instance):
        return [
            reverse(
                "team-detail",
                kwargs={"uuid": t.uuid},
                request=self.context.get("request", None),
            )
            for t in instance.teams.all()
        ]

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "teams",
        )


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[validators.UniqueValidator(queryset=User.objects.all())],
    )

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "password2",
            "email",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        user.set_password(validated_data["password"])
        user.save()

        return user


class MembershipSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name")
    username = serializers.CharField(source="user.username")

    class Meta:
        model = account_models.Membership
        fields = (
            "id",
            "created",
            "modified",
            "team_name",
            "username",
            "role",
        )


class TeamSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="team-detail", lookup_field="uuid"
    )
    memberships = MembershipSerializer(many=True, read_only=True)
    # users = serializers.HyperlinkedRelatedField(
    #     queryset=User.objects.all(),
    #     view_name='user-detail',
    #     many=True,
    #     # lookup_field='uuid',
    #     required=False  # for update
    # )
    # users = UserSerializer(many=True, read_only=True)
    # owner = serializers.HyperlinkedRelatedField(
    #     queryset=User.objects.all(),
    #     view_name='user-detail',
    #     required=False  # for update
    # )

    class Meta:
        model = account_models.Team
        fields = (
            "id",
            "uuid",
            "name",
            "created",
            "modified",
            "url",
            "memberships",
        )


class TeamUserAddSerializer(serializers.Serializer):
    users = serializers.HyperlinkedRelatedField(
        queryset=User.objects.all(),
        many=True,
        # read_only=True,
        view_name="user-detail",
    )


class InvitationSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedIdentityField(
        view_name="invitation-detail", lookup_field="uuid"
    )
    team = serializers.HyperlinkedRelatedField(
        queryset=account_models.Team.objects.all(),
        lookup_field="uuid",
        view_name="team-detail",
    )

    invited_by = serializers.ReadOnlyField(source="invited_by.get_display_name")

    class Meta:
        model = account_models.Invitation
        fields = (
            "id",
            "url",
            "uuid",
            "created",
            "modified",
            "team",
            "email",
            "role",
            "invited_by",
            "is_accepted",
        )


class AccountAPIKeySerializer(serializers.HyperlinkedModelSerializer):
    team = serializers.HyperlinkedRelatedField(
        queryset=account_models.Team.objects.all(),
        lookup_field="uuid",
        view_name="team-detail",
        required=True,
    )
    user = serializers.HyperlinkedRelatedField(
        view_name="user-detail", required=False, read_only=True
    )

    class Meta:
        model = account_models.AccountAPIKey
        fields = (
            "id",
            "uuid",
            "key",
            "team",
            "user",
            "prefix",
            "created",
            "name",
            "revoked",
            "expiry_date",
        )
        read_only_fields = (
            "uuid",
            "key",
            "prefix",
            "created",
            "revoked",
            "expiry_date",
        )

    def validate(self, attrs):
        if attrs["name"] in account_models.User.objects.all().values_list(
            "username", flat=True
        ):
            raise exceptions.ValidationError("name must be unique for username")

        # if not attrs['user'].is_configuration_member(attrs['team']):
        #     raise exceptions.ValidationError('user must be configuration')
        return attrs

    def create(self, validated_data):
        user_ = account_models.User.objects.create_user(
            username=validated_data["name"],
            password="test",
            email=f'{validated_data["name"]}@test.test',
        )
        account_models.Membership.objects.create(
            user=user_,
            team=validated_data["team"],
            role=account_models.Membership.Role.CONFIGURATION,
        )
        api_key_obj, key = account_models.AccountAPIKey.objects.create_key(
            name=validated_data["name"]
        )
        api_key_obj.user = user_
        api_key_obj.team = validated_data["team"]
        api_key_obj.key = key
        api_key_obj.save()
        return api_key_obj
