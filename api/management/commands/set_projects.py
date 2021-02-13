import json

from django.core.management import BaseCommand, CommandError

from api.models import UserProfile, Client
from api.serializers import ProjectSerializer, ClientSerializer, ClientShortSerializer


class Command(BaseCommand):
    help = 'Get my projects'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)

    def handle(self, *args, **options):
        for username in options['username']:
            profile = UserProfile.get(username)
            if not profile:
                raise CommandError('UserProfile "%s" does not exist' % username)
            profile.all_projects.all().delete()
            profile.clients.all().delete()
            file = open('test.txt')
            text = file.read()
            print(text)
            projects = json.loads(text)
            print(json.dumps(text, sort_keys=True, indent=4))
            for project in projects:

                if project.get('client'):
                    print(project['client'])
                    if profile.clients.filter(name=project['client']['name'], company=project['client']['company']).first():
                        continue
                    serializer = ClientShortSerializer(data=project['client'])
                    if serializer.is_valid():
                        serializer.save(user=profile)
                        print(f'client was add')

                project['creator'] = project['user']
                if not project.get('title'):
                    project['creator'] = None
                print(project)
                serializer = ProjectSerializer(data=project)
                if serializer.is_valid():
                    serializer.save()
                    print(f'project was add')
                else:
                    print(serializer.errors)
