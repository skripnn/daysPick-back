from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Copy user.profile to profile field'

    def handle(self, *args, **kwargs):
        from api.models import Project

        def profile(i):
            if i.title:
                i.creator = i.user
                i.save()
                print(f'{i} - ok')

        [profile(i) for i in Project.objects.all()]

