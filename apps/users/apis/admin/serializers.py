from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


# ─────────────────────────────────────────────
#  PERMISSION (read-only, group assign üçün)
# ─────────────────────────────────────────────

class AdminPermissionSerializer(serializers.ModelSerializer):
    content_type_label = serializers.CharField(
        source="content_type.app_label", read_only=True
    )
    content_type_model = serializers.CharField(
        source="content_type.model", read_only=True
    )

    class Meta:
        model = Permission
        fields = ("id", "name", "codename", "content_type_label", "content_type_model")


# ─────────────────────────────────────────────
#  GROUP (Qruplar)
# ─────────────────────────────────────────────

class AdminGroupListSerializer(serializers.ModelSerializer):
    """Siyahı — permissions count əlavə edir"""
    permissions_count = serializers.IntegerField(
        source="permissions.count", read_only=True
    )

    class Meta:
        model = Group
        fields = ("id", "name", "permissions_count")


class AdminGroupDetailSerializer(serializers.ModelSerializer):
    """Detal — tam permissions siyahısı"""
    permissions = AdminPermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ("id", "name", "permissions")


class AdminGroupWriteSerializer(serializers.ModelSerializer):
    """Yarat / Yenilə — permission ID-ləri ilə"""
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )

    class Meta:
        model = Group
        fields = ("name", "permissions")

    def validate_name(self, value):
        qs = Group.objects.filter(name=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu adda qrup artıq mövcuddur.")
        return value


# ─────────────────────────────────────────────
#  USER (İstifadəçilər)
# ─────────────────────────────────────────────

class AdminUserGroupSerializer(serializers.ModelSerializer):
    """Nested qrup — user list/detail üçün"""
    class Meta:
        model = Group
        fields = ("id", "name")


class AdminUserListSerializer(serializers.ModelSerializer):
    """Siyahı — yüngül, groups adları ilə"""
    full_name = serializers.CharField(source="get_full_name", read_only=True)
    groups = AdminUserGroupSerializer(many=True, read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "full_name",
            "first_name",
            "last_name",
            "type",
            "is_staff",
            "is_active",
            "groups",
            "date_joined",
        )


class AdminUserDetailSerializer(AdminUserListSerializer):
    """Detal — user_permissions də əlavə olunur"""
    user_permissions = AdminPermissionSerializer(many=True, read_only=True)

    class Meta(AdminUserListSerializer.Meta):
        fields = AdminUserListSerializer.Meta.fields + (
            "email",
            "is_superuser",
            "user_permissions",
            "last_login",
        )


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Yeni istifadəçi yarat.
    Admin UI-dakı add_fieldsets ilə eyni sahələr:
      username, password, password2, type, is_staff, is_active
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, label="Şifrənin təsdiqi")
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "password",
            "password2",
            "type",
            "is_staff",
            "is_active",
            "groups",
        )
        extra_kwargs = {
            "is_active": {"default": True},
            "is_staff": {"default": False},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu istifadəçi adı artıq istifadə edilir.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Şifrələr uyğun deyil."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        user = User.objects.create_user(**validated_data)
        if groups:
            user.groups.set(groups)
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Mövcud istifadəçini yenilə.
    Şifrə isteğe bağlıdır — göndərilsə dəyişdirilir.
    """
    password = serializers.CharField(
        write_only=True, min_length=8, required=False, allow_blank=True
    )
    password2 = serializers.CharField(
        write_only=True, required=False, allow_blank=True, label="Şifrənin təsdiqi"
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, required=False
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
            "password2",
            "type",
            "is_staff",
            "is_active",
            "groups",
        )

    def validate_username(self, value):
        qs = User.objects.filter(username=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu istifadəçi adı artıq istifadə edilir.")
        return value

    def validate(self, attrs):
        pw = attrs.get("password", "")
        pw2 = attrs.pop("password2", "")
        if pw or pw2:
            if pw != pw2:
                raise serializers.ValidationError({"password2": "Şifrələr uyğun deyil."})
            try:
                validate_password(pw)
            except DjangoValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})
        else:
            attrs.pop("password", None)
        return attrs

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)

        if password:
            instance.set_password(password)

        instance.save()

        if groups is not None:
            instance.groups.set(groups)

        return instance


class AdminUserSetPasswordSerializer(serializers.Serializer):
    """Şifrəni dəyişdir (ayrı endpoint)"""
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password2": "Şifrələr uyğun deyil."})
        try:
            validate_password(attrs["password"])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs
