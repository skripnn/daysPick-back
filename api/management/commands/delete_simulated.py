from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Delete simulated accounts'

    def handle(self, *args, **options):
        from api.models import User
        users = User.objects.filter(is_staff=True, is_superuser=False)
        if not len(users):
            print('Аккаунты не найдены')
        for user in users:
            if user.account and user.account.profile:
                user.account.profile.delete()
                print(f'Аккаунт {user.account.username} удален')
