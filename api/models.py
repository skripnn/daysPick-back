import re
from datetime import datetime

from django.contrib.auth.models import User, AbstractUser
from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models
from django.db.models import Q
from django.utils import timezone
from mptt.models import MPTTModel, TreeForeignKey
from pyaspeller import YandexSpeller
from django.utils.translation import gettext_lazy as _

null = {'null': True, 'blank': True}


class Tag(MPTTModel):
    class Category(models.IntegerChoices):
        NONE = 0, _('')
        SOUND = 1, _('Звук')
        LIGHT = 2, _('Свет')

    category = models.IntegerField(choices=Category.choices, default=0)
    title = models.CharField(max_length=64)
    parent = TreeForeignKey('self', on_delete=models.SET_NULL, related_name='children', **null)
    info = models.TextField(**null)
    custom = models.BooleanField(default=True)

    class MPTTMeta:
        order_insertion_by = ['title']

    def __str__(self):
        return self.title


class ProfileTagManager(models.Manager):
    use_for_related_fields = True

    def list(self):
        return [i.tag for i in self.get_queryset()]

    def update(self, data):
        tags = []
        for rank, i in enumerate(data):
            tag = Tag.objects.get(**i)
            profile_tag, created = self.get_or_create(tag=tag)
            if profile_tag.rank != rank:
                profile_tag.rank = rank
                profile_tag.save()
            tags.append(profile_tag)
        self.set(tags)
        ProfileTag.objects.filter(user__isnull=True).delete()
        Tag.objects.filter(profile_tags__user__isnull=True, custom=True).delete()
        return self.list()


class ProfileTag(models.Model):
    class Meta:
        ordering = ['user', 'rank']

    tag = models.ForeignKey('Tag', on_delete=models.CASCADE, related_name='profile_tags')
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE, related_name='tags', null=True)
    rank = models.IntegerField(default=0)

    objects = ProfileTagManager()


class ClientsManager(models.Manager):
    use_for_related_fields = True

    def search(self, **kwargs):
        if not kwargs:
            return self.get_queryset().all()

        search = kwargs.get('filter')
        name = kwargs.get('name')
        company = kwargs.get('company')
        days = kwargs.get('days')
        clients = self.get_queryset()

        if search:
            search = search[0]
            spelled = YandexSpeller().spelled(search)
            options = [option for option in spelled.split(' ') if len(option) > 1]
            vector = SearchVector('name', 'company')
            clients = clients.filter(
                Q(name__icontains=search) |
                Q(company__icontains=search) |
                Q(name__icontains=spelled) |
                Q(company__icontains=spelled) |
                Q(name__in=options) |
                Q(company__in=options)
            ).annotate(rank=SearchRank(vector, search)).order_by('-rank')

        if name:
            name = name[0]
            clients = clients.filter(name__icontains=name)

        if company:
            company = company[0]
            clients = clients.filter(company__icontains=company)

        if days:
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            clients = clients.filter(projects__days__date__in=dates).distinct()

        return clients


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(max_length=64, **null)
    last_name = models.CharField(max_length=64, **null)
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
    def create(cls, **kwargs):
        username = kwargs.pop('username')
        password = kwargs.pop('password')
        password2 = kwargs.pop('password2')
        profile = cls.objects.create(**kwargs, user=User.objects.create_user(username=username, password=password))
        if profile and profile.email:
            profile.send_confirmation_email()
        return profile


    @classmethod
    def get(cls, username, alt=None):
        if not username:
            return alt
        if isinstance(username, User):
            return cls.objects.filter(user=username).first() or alt
        if isinstance(username, str):
            if re.match('^79[0-9]{9}$', username):
                phone = username
                return cls.objects.filter(phone_confirm=phone).first() or alt
        return cls.objects.filter(user__username=username).first() or alt

    @classmethod
    def search(cls, **kwargs):
        users = cls.objects.exclude(email_confirm__isnull=True, phone_confirm__isnull=True)
        if kwargs.get('filter'):
            search = kwargs['filter'][0]
            words = search.split(' ')
            if len(words) == 1 and not words[0]:
                return []
            spelled = YandexSpeller().spelled(search)
            options = [option for option in spelled.split(' ') if len(option) > 1]
            phones = re.findall('9[0-9]{2}.{,2}[0-9]{3}.?[0-9]{2}.?[0-9]{2}', search)
            phones = ['7' + ''.join(re.findall('[0-9]', phone)[:10]) for phone in phones]
            vector = SearchVector('user__username', 'first_name', 'last_name', 'phone')
            users = users.filter(
                Q(user__username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(user__username__in=words) |
                Q(first_name__in=words) |
                Q(last_name__in=words) |
                Q(phone_confirm__in=phones) |
                Q(tags__tag__title__icontains=search) |
                Q(tags__tag__parent__title__icontains=search) |
                Q(user__username__icontains=spelled) |
                Q(first_name__icontains=spelled) |
                Q(last_name__icontains=spelled) |
                Q(user__username__in=options) |
                Q(first_name__in=options) |
                Q(last_name__in=options) |
                Q(tags__tag__title__icontains=spelled) |
                Q(tags__tag__parent__title__icontains=spelled)
            ).annotate(rank=SearchRank(vector, search)).order_by('-rank').distinct()
        if kwargs.get('days'):
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            users = users.exclude(all_projects__days__date__in=dates)
        return users

    def get_actual_projects(self, asker):
        today = timezone.now().date()
        if asker == self:
            return self.projects.filter(Q(date_end__gte=today) | Q(is_paid=False)).reverse()
        if not asker:
            return None
        return self.projects.filter(creator=asker).reverse()

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

    def __str__(self):
        return self.user.username

    def __repr__(self):
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
    def search(self, **kwargs):
        search = kwargs.get('filter')
        days = kwargs.get('days')

        projects = self

        if search:
            search = search[0]
            spelled = YandexSpeller().spelled(search)
            options = [option for option in spelled.split(' ') if len(option) > 1]
            vector = SearchVector('title', 'client__name', 'client__company')
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(client__name__icontains=search) |
                Q(client__company__icontains=search) |
                Q(title__icontains=spelled) |
                Q(client__name__icontains=spelled) |
                Q(client__company__icontains=spelled) |
                Q(title__in=options) |
                Q(client__name__in=options) |
                Q(client__company__in=options)
            ).annotate(rank=SearchRank(vector, search)).order_by('-rank')

        if days:
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            projects = projects.filter(days__date__in=dates).distinct()

        return projects


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
        ordering = ['date', 'project__date_start', 'project__date_end']

    date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='days', null=True)
    info = models.TextField(**null)

    def __str__(self):
        return ' - '.join([str(self.project), str(self.date)])
