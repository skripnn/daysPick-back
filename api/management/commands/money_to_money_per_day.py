from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Add money per day field from money field'

    def handle(self, *args, **kwargs):
        from api.models import Project
        projects = Project.objects.all()
        for project in projects:
            if project.money:
                project.money_per_day = project.money / project.days.count()
                project.save()
                print(f'Project {project.id}: {project.money} / {project.days.count()} = {project.money_per_day}')
