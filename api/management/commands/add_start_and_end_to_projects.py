from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Add start and end fields to project from dates'

    def handle(self, *args, **kwargs):
        from api.models import Project
        test = Project.objects.all()
        for project in test:
            project.date_start = project.dates[0]
            project.date_end = project.dates[-1]
            project.save()
