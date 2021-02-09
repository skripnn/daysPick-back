from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Create days off project and parse days off from user profile'

    def handle(self, *args, **kwargs):
        from api.models import UserProfile, Project, Day
        for profile in UserProfile.objects.all():
            print(f'user {profile.user}:')
            dof, created = Project.objects.get_or_create(user=profile.user, creator__isnull=True)
            print(f'Days off project was {"created" if created else "founded"}')
            days = []
            for date in profile.days_off:
                day, created = Day.objects.get_or_create(project=dof, date=date)
                print(f'Day for {date} was {"created" if created else "founded"}')
                days.append(day)
            dof.days.set(days)
        Day.objects.filter(project=None).delete()

