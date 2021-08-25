from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Parse fields from userprofile to profile and account'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile
        profiles = UserProfile.objects.all()
        for profile in profiles:
            print(f'start - {profile.username}')
            account = profile.user.account
            if not account:
                print(f'wrong - {profile.username}')
                continue
            profile.account = account
            profile.save()
            print(f'ok - {profile.username}')
