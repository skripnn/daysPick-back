from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Parse fields from userprofile to profile and account'

    def handle(self, *args, **kwargs):
        from api.models import ProfileTag
        tags = ProfileTag.objects.all()
        for tag in tags:
            tag.user = tag.profile.account
            tag.save()
            print(f'ok - {tag.id}')
