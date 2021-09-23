import datetime
import random

from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Create random projects'

    def handle(self, *args, **options):
        from api.models import UserProfile
        profile = UserProfile.get(options.get('user'))
        if not profile:
            from api.models import Account
            try:
                n = int(options.get('number'))
            except:
                n = 1
            for i in range(n):
                account = Account.create(password='qwerty')
                account.update(email_confirm=f'{account.username}@dayspick.ru')
                profile = account.profile
                profile.update(first_name='Тестовый пользователь', last_name=f'{account.username}')
                print(f'\nСоздан пользователь {profile.full_name}')
                create_random_projects(profile)

        else:
            create_random_projects(profile)

    def add_arguments(self, parser):
        parser.add_argument(
            '-u',
            '--user',
            action='store',
            default=None,
            help='Пользователь (id или username)'
        )
        parser.add_argument(
            '-n',
            '--number',
            action='store',
            default=1,
            help='Количество новых пользователей'
        )


def create_random_projects(profile):
    for _ in range(random.randint(1, 10)):
        project = profile.create_project({
            'title': None,
            'days': random_days(),
            'money': None,
            'money_calculating': False,
            'money_per_day': None,
            'client': None,
            'user': profile.id,
            'canceled': None,
            'is_paid': False,
            'is_wait': False,
            'info': None,
            'parent': None,
            'confirmed': True,
            'is_series': False
        })
        print(f'Создан проект {project.get_title()}')


def random_days():
    date = datetime.datetime.now() + datetime.timedelta(days=random.randint(0, 60))
    days = {}
    for a in range(random.randint(1, 14)):
        days[date.strftime('%Y-%m-%d')] = None
        date = date + datetime.timedelta(days=1)
    return days
