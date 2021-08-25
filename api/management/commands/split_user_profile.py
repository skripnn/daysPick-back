from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Parse fields from userprofile to profile and account'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile, Profile
        user_profiles = UserProfile.objects.all()
        for user_profile in user_profiles:
            profile_fields = {
                'user': user_profile,
                'first_name': user_profile.first_name,
                'last_name': user_profile.last_name,
                'avatar': user_profile.avatar,
                'photo': user_profile.photo,
                'email': user_profile.contacts.email,
                'phone': user_profile.contacts.phone,
                'telegram': user_profile.contacts.telegram,
                'info': user_profile.info
            }
            Profile.objects.create(**profile_fields)
            print(f'ok - {user_profile.username}')
