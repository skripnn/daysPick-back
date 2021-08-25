from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Parse fields from userprofile to account'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile, Account
        user_profiles = UserProfile.objects.all()
        for user_profile in user_profiles:
            account_fields = {
                'user': user_profile.user
            }
            for field in [
                'email',
                'email_confirm',
                'phone',
                'phone_confirm',
                'telegram_chat_id',
                'facebook_account',
                'is_public',
                'raised',
            ]:
                account_fields[field] = getattr(user_profile, field)
            Account.objects.create(**account_fields)
            print(f'ok - {user_profile.username}')
