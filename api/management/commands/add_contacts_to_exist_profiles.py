from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Add Contacts to all profiles'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile, Contacts
        profiles = UserProfile.objects.all()
        for profile in profiles:
            Contacts.objects.create(user=profile)
            print(f'Contacts model for {profile.username} was created')
