from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Parse fields from userprofile to profile and account'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile
        profiles = UserProfile.objects.all()
        for profile in profiles:
            print(f'start - {profile.username}')
            profile.email = profile.contacts.email
            profile.phone = profile.contacts.phone
            profile.telegram = profile.contacts.telegram
            profile.save()
            print(f'ok - {profile.username}')
