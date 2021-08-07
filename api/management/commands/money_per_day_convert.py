from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Convert money per day from int to float'

    def handle(self, *args, **kwargs):
        from api.models import Project
        projects = Project.objects.all()
        for project in projects:
            if project.days.count() and project.money and not project.money_calculating:
                project.money_per_day = project.money / project.days.count()
                project.save()
                print(f'Project {project.id}: {project.money} / {project.days.count()} = {project.money_per_day}')
