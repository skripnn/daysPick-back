from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Convert dates field from Project to Day models'

    def handle(self, *args, **kwargs):
        from api.models import Project, Day
        projects = Project.objects.all()
        for project in projects:
            for date in project.dates:
                Day.objects.create(date=date, project=project)
