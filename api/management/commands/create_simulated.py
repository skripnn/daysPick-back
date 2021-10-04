import datetime
import random

from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Create simulated accounts'

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
                account.user.is_staff = True
                account.user.save()
                profile = account.profile
                random_name(profile)
                random_tags(profile)

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
    for a in range(random.randint(1, 8)):
        days[date.strftime('%Y-%m-%d')] = None
        date = date + datetime.timedelta(days=1)
    return days


def random_name(profile):
    import requests
    import bs4 as bs

    r = requests.get('https://randomus.ru/name?type=2&sex=10&count=1')
    soup = bs.BeautifulSoup(r.text, 'html.parser')
    first_name, last_name = soup.select_one('#result_textarea').text.split(' ')
    profile.update(first_name=first_name, last_name=last_name)


def random_tags(profile):
    from api.models import Tag
    from api.serializers import TagSerializer
    tags = random.sample(set(Tag.objects.filter(default=True)), random.randint(0, 3))
    profile.tags.update(TagSerializer(tags, many=True).data)