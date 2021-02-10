from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Copy user.profile to profile field'

    def handle(self, *args, **kwargs):
        from api.models import Project, Client

        def profile(i):
            i.profile = i.user.profile
            i.save()
            print(f'{i} - ok')

        [profile(i) for i in Project.objects.all()]
        [profile(i) for i in Client.objects.all()]

