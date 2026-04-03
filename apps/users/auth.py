from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import authentication, exceptions

User = get_user_model()


class PINAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        pin = request.headers.get('X-PIN')
        if not pin:
            return None

        try:
            user = User.objects.get(username=pin)
            if not user.is_active:
                raise exceptions.AuthenticationFailed(
                    'User account is inactive')
            return (user, None)
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('No such user')

        return None


class AdminTokenAuthentication(authentication.BaseAuthentication):
    """
    Admin panel üçün token-based authentication.
    Header: Authorization: Bearer <token>
    """
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token_key = auth_header.split(' ', 1)[1].strip()

        try:
            from apps.users.models.token import AdminAuthToken
            token_obj = AdminAuthToken.objects.select_related('user').get(token=token_key)
        except AdminAuthToken.DoesNotExist:
            raise exceptions.AuthenticationFailed('Yanlış və ya etibarsız token.')

        if token_obj.is_expired:
            raise exceptions.AuthenticationFailed('Token-in müddəti bitib. Yenidən daxil olun.')

        if not token_obj.user.is_active:
            raise exceptions.AuthenticationFailed('İstifadəçi hesabı deaktivdir.')

        # Son istifadə tarixini yenilə
        token_obj.last_used_at = timezone.now()
        token_obj.save(update_fields=['last_used_at'])

        return (token_obj.user, token_obj)

    def authenticate_header(self, request):
        return 'Bearer'

