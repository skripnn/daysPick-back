from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'Parse fields from userprofile to profile and account'

    def handle(self, *args, **kwargs):
        from api.models import Project
        projects = Project.objects.filter(children__isnull=False).distinct()
        for project in projects:
            print(f'start - {project.title}')
            project.update(is_series=True)
            print(f'ok - {project.title}')
