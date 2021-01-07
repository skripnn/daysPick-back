from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Transform name to company'

    def handle(self, *args, **kwargs):
        from api.models import Client
        clients = Client.objects.all()
        for client in clients:
            x = input(f'{str(client)}. Transform? [y/N]')
            if x == 'y':
                name = input(f'Input Name:')
                client.company = client.name
                client.name = name
                client.save()