import json
from pprint import pprint

from django.core.management import BaseCommand, CommandError

from api.models import UserProfile
from api.serializers import ProjectSerializer, ClientShortSerializer


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
            projects = json.loads(text)
            for project in projects:

                if project.get('client'):
                    client = profile.clients.filter(name=project['client']['name'], company=project['client']['company']).first()
                    if not client:
                        serializer = ClientShortSerializer(data=project['client'])
                        if serializer.is_valid():
                            serializer.save(user=profile)
                            print(f'client was add')

                project['creator'] = project['user']
                if not project.get('title'):
                    project['creator'] = None
                serializer = ProjectSerializer(data=project)
                if serializer.is_valid():
                    serializer.save()
                    print(f'project was add')
                else:
                    pprint(project)
                    print(serializer.errors)
