from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authtoken.models import Token
from re import sub

from api.models import UserProfile


class UpdateLastActivityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        header_token = request.META.get('HTTP_AUTHORIZATION', None)
        if header_token is not None:
            try:
                token = sub('Token ', '', request.META.get('HTTP_AUTHORIZATION', None))
                token_obj = Token.objects.get(key=token)
                profile = UserProfile.get(token_obj.user)
                if profile:
                    profile.update(last_activity=timezone.now())
            except Token.DoesNotExist:
                pass
