import json

from django.core.management import BaseCommand, CommandError

from api.models import UserProfile
from api.serializers import ProjectSerializer


class Command(BaseCommand):
    help = 'Get my projects'

    def add_arguments(self, parser):
        parser.add_argument('username', nargs='+', type=str)

    def handle(self, *args, **options):
        for username in options['username']:
            profile = UserProfile.get(username)
            if not profile:
                raise CommandError('UserProfile "%s" does not exist' % username)
            projects = profile.all_projects
            serializer = ProjectSerializer(projects, many=True)
            file = open('test.txt', 'w')
            file.write(json.dumps(serializer.data))
            print('ok')