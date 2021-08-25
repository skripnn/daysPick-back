from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Add Client from Project.Client(CharField)'

    def handle(self, *args, **kwargs):
        from api.models import Project, Client
        projects = Project.objects.all()
        for project in projects:
            project.clientModel = Client.objects.get(user=project.account, name=project.client)
            project.save()
            print(f'project.client "{project.client}" -> project.clientModel')
