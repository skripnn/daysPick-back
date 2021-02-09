from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Convert dates field from Project to Day models'

    def handle(self, *args, **kwargs):
        from api.models import Project, Day
        projects = Project.objects.all()
        for project in projects:
            for date in project.dates:
                day, created = Day.objects.get_or_create(date=date, project=project)
                if created:
                    print(f'Day {date.strftime("%d-%m-%Y")} for project {project.id} was created.')
