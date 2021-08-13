from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Add start and end fields to project from dates'

    def handle(self, *args, **kwargs):
        from api.models import Project
        test = Project.objects.all().folders()
        for project in test:
            project.parent_days_set()
