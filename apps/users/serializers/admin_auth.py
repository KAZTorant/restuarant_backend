from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

ADMIN_TYPES = ('admin', 'restaurant')


def _is_admin_user(user) -> bool:
    """
    İstifadəçinin admin panelə girişi var-yox yoxlayır.
    Aşağıdakı hallarda keçərlidir:
      1. is_superuser=True  → Django admin hesabı
      2. is_staff=True      → Django staff hesabı
      3. type in ('admin', 'restaurant') → App admin/owner hesabı
    """
    if user.is_superuser or user.is_staff:
        return True
    return user.type in ADMIN_TYPES


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {'username': 'İstifadəçi adı yanlışdır.'}
            )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {'password': 'Şifrə yanlışdır.'}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {'username': 'Bu hesab deaktivdir.'}
            )

        if not _is_admin_user(user):
            raise serializers.ValidationError(
                {'username': 'Bu hesabın admin panelinə girişi yoxdur. '
                             '(admin, restaurant, superuser və ya staff olmalıdır)'}
            )

        attrs['user'] = user
        return attrs


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'full_name',
            'first_name',
            'last_name',
            'email',
            'type',
            'is_active',
            'is_superuser',
            'is_staff',
        )
