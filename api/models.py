import re

from django.contrib.auth.models import User, AbstractUser
from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

null = {'null': True, 'blank': True}


class Telegram(models.Model):
    chat_id = models.IntegerField()
    profile = models.ForeignKey('UserProfile', on_delete=models.CASCADE, **null, related_name='telegram_phone_confirm')


class ClientsManager(models.Manager):
    use_for_related_fields = True

    def search(self, filter=None, name=None, company=None):
        queryset = self.get_queryset()
        if filter:
            vector = SearchVector('name', 'company')
            return queryset.filter(Q(name__icontains=filter) | Q(company__icontains=filter)) \
                .annotate(rank=SearchRank(vector, filter)).order_by('-rank')

        if name and company:
            return queryset.filter(company__istartswith=company, name__istartswith=name)

        if name:
            return queryset.filter(name__istartswith=name)

        if company:
            return queryset.filter(company__istartswith=company)

        return queryset.all()


class Position(models.Model):
    class Meta:
        ordering = ['title']

    title = models.CharField(max_length=64)

    def __str__(self):
        return self.title

    def __repr__(self):
        return self.title


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=64, **null)
    last_name = models.CharField(max_length=64, **null)
    positions = models.ManyToManyField('Position', related_name='profiles', blank=True)
    email = models.EmailField(**null)
    email_confirm = models.EmailField(**null)
    phone = models.CharField(max_length=32, **null)
    phone_confirm = models.CharField(max_length=32, **null)
    telegram_chat_id = models.IntegerField(**null)

    @property
    def is_confirmed(self):
        return bool(self.email_confirm or self.phone_confirm)

    @property
    def full_name(self):
        full_name = self.username
        if self.first_name:
            full_name = self.first_name
        if self.last_name:
            full_name += ' ' + self.last_name
        return full_name

    @property
    def username(self):
        return self.user.username

    @property
    def projects(self):
        return self.all_projects.exclude(creator__isnull=True)

    @property
    def days_off_project(self):
        return self.all_projects.filter(creator__isnull=True).first()

    @classmethod
    def get(cls, username, alt=None):
        if not username:
            return alt
        if isinstance(username, User):
            return cls.objects.filter(user=username).first() or alt
        if isinstance(username, str):
            if re.match('^[0-9]{11}$', username):
                p = username
                phone = f'+{p[0]} ({p[1:4]}) {p[4:7]}-{p[7:9]}-{p[9:]}'
                return cls.objects.filter(phone_confirm=phone).first() or alt
        return cls.objects.filter(user__username=username).first() or alt

    def get_actual_projects(self, asker):
        today = timezone.now().date()
        if asker == self:
            return self.projects.filter(Q(date_end__gte=today) | Q(is_paid=False))
        if not asker:
            return None
        return self.projects.filter(creator=asker)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
            if key == 'email' and value:
                self.send_confirmation_email()
        self.save()
        return self

    def send_confirmation_email(self):
        code = hash(self.email)
        print('send', self.email, code)
        letter = {
            'theme': 'DaysPick e-mail confirmation',
            'body': f'Confirm your account {self.username} on link: http://dayspick.ru/confirm/?user={self.username}&code={code}',
            'from': 'DaysPick <registration@dayspick.ru>',
            'to': [self.email]
        }
        print(f'http://dayspick.ru/confirm/?user={self.username}&code={code}')
        try:
            from django.core.mail import send_mail
            send_mail(letter['theme'],
                      letter['body'],
                      letter['from'],
                      letter['to'])
        except Exception as e:
            print(f'SEND MAIL ERROR: {e}')

    def confirm_email(self, code):
        hash_code = hash(self.email)
        print('confirm', self.email, hash_code)
        if str(hash_code) == code:
            self.update(email_confirm=self.email, email=None)
            return True
        return False

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            profile = UserProfile.objects.create(user=instance, email=instance.email)
            profile.all_projects.create()

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        if not instance.is_superuser:
            instance.profile.save()

    def __str__(self):
        return self.user.username


class Client(models.Model):
    class Meta:
        ordering = ['company', 'name']

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=64)
    company = models.CharField(max_length=64, **null, default='')

    objects = ClientsManager()

    def __str__(self):
        return ' - '.join([str(self.user), f'{self.name} ({self.company})'])


class ProjectsQuerySet(models.QuerySet):
    def search(self, search=None):
        if not search:
            return self

        vector = SearchVector('title', 'client__name', 'client__company')
        return self.filter(
            Q(title__icontains=search) | Q(client__name__icontains=search) | Q(client__company__icontains=search)) \
            .annotate(rank=SearchRank(vector, search)).order_by('-rank')


class ProjectsManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return ProjectsQuerySet(self.model, using=self._db)


class Project(models.Model):
    class Meta:
        ordering = ['-date_end', '-date_start']

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='all_projects')
    creator = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, related_name='created_projects', **null)
    date_start = models.DateField(**null)
    date_end = models.DateField(**null)
    title = models.CharField(max_length=64, **null)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, **null, related_name='projects')
    money = models.IntegerField(**null)
    money_per_day = models.IntegerField(**null)
    money_calculating = models.BooleanField(default=False)
    info = models.TextField(**null)
    is_paid = models.BooleanField(default=False)

    objects = ProjectsManager()

    @property
    def dates(self):
        return [i.date for i in self.days.all()]

    def __str__(self):
        return ' - '.join([str(self.user), str(self.id), str(self.title or '*days_off*')])


class Day(models.Model):
    class Meta:
        ordering = ['date']

    date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='days', null=True)
    info = models.TextField(**null)

    def __str__(self):
        return ' - '.join([str(self.project), str(self.date)])
