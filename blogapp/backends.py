from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailBackend(ModelBackend):
    """Authenticate by email + password instead of username + password."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Django internals pass credentials as the username param; we treat it as email
        email = kwargs.get('email', username)
        if not email or not password:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Multiple users share the same email — pick the first active one
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if not user:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
