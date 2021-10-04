import re
import uuid
from datetime import datetime, timedelta
from functools import reduce

from django.contrib.auth.models import User, AbstractUser
from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models, OperationalError
from django.db.models import Q, Count, F, Case, When, BooleanField
from django.utils import timezone
from pyaspeller.yandex_speller import YandexSpeller

from api.mail import Mail

null = {'null': True, 'blank': True}


class Tag(models.Model):
    title = models.CharField(max_length=64)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    @classmethod
    def search(cls, **kwargs):
        search = kwargs.get('filter')
        profile = kwargs.get('profile')
        exclude = kwargs.get('exclude', [])
        tags = cls.objects.exclude(id__in=exclude)

        if profile:
            tags = cls.objects.exclude(profile_tags__user=profile)

        if search:
            if isinstance(search, list):
                search = search[0]
            try:
                spelled = YandexSpeller().spelled(search)
            except:
                spelled = search

            exact = tags.filter(title__iexact=search)
            exact_spelled = tags.filter(title__iexact=spelled)
            starts = tags.filter(title__istartswith=search)
            starts_spelled = tags.filter(title__istartswith=spelled)
            contain = tags.filter(title__icontains=search)
            contain_spelled = tags.filter(title__icontains=spelled)

            tags = exact | exact_spelled | starts | starts_spelled | contain | contain_spelled

        tags = tags.annotate(num_of_uses=Count('profile_tags')).order_by('-num_of_uses')

        return tags[:15]


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
        Tag.objects.filter(profile_tags__user__isnull=True).exclude(default=True).delete()
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
            if isinstance(search, list):
                search = search[0]
            try:
                spelled = YandexSpeller().spelled(search)
            except:
                spelled = search
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
            if isinstance(name, list):
                name = name[0]
            clients = clients.filter(name__icontains=name)

        if company:
            if isinstance(company, list):
                company = company[0]
            clients = clients.filter(company__icontains=company)

        if days:
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            clients = clients.filter(projects__days__date__in=dates).distinct()

        return clients


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='account', primary_key=True)
    email = models.EmailField(**null)
    email_confirm = models.EmailField(**null, unique=True)
    phone = models.CharField(max_length=32, **null)
    phone_confirm = models.CharField(max_length=32, **null, unique=True)
    telegram_chat_id = models.IntegerField(**null, unique=True)
    facebook_account = models.OneToOneField('FacebookAccount', on_delete=models.SET_NULL, **null,
                                            related_name='account')
    is_public = models.BooleanField(default=False)
    raised = models.DateTimeField(default=timezone.now)
    favorites = models.ManyToManyField('UserProfile', related_name='favorite_of', blank=True)

    telegram_notifications = models.BooleanField(default=False)

    @property
    def can_be_raised(self):
        delta = timezone.now() - self.raised
        return delta > timedelta(hours=3)

    @property
    def username(self):
        if not self.user:
            return None
        return self.user.username

    @property
    def is_confirmed(self):
        return bool(self.email_confirm or self.phone_confirm)

    def token(self, new=False):
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=self.user)
        if new and not created:
            token.delete()
            token = Token.objects.create(user=self.user)
        return token.key

    @classmethod
    def get(cls, username, alt=None):
        if not username:
            return alt
        from rest_framework.request import Request
        if isinstance(username, Request):
            username = username.user
        if isinstance(username, User):
            return username.account
        if isinstance(username, cls):
            return username
        if str(username).isdigit():
            params = {'profile__id': int(username)}
        else:
            params = {'user__username': username}
        return cls.objects.filter(**params).first() or alt

    @classmethod
    def create(cls, **data):
        username = data.pop('username', None)
        password = data.pop('password', uuid.uuid4().hex)
        data.pop('password2', None)
        user = User.objects.create_user(username=username or f'u{uuid.uuid4().hex[:16]}', password=password)
        account = cls.objects.create(user=user, **data)
        UserProfile.objects.create(account=account)
        if not username:
            account.update(username=str(account.profile.id))
        from api.bot import BotNotification
        BotNotification.send_to_admins(f'Аккаунт создан.\nusername: {account.username}')
        if account and account.email:
            account.send_confirmation_email()
        return account

    def update(self, **data):
        for key, value in data.items():
            if key == 'favorite':
                profile = UserProfile.get(value)
                if not profile:
                    continue
                if self.favorites.filter(id=value):
                    self.favorites.remove(profile)
                else:
                    self.favorites.add(profile)
                continue
            if key == 'raised':
                if self.can_be_raised:
                    self.raised = timezone.now()
                continue
            if key == 'username' and value:
                self.user.username = value
                self.user.save()
                continue
            if key == 'password' and value:
                self.user.set_password(value)
                self.user.save()
                from rest_framework.authtoken.models import Token
                token = Token.objects.filter(user=self.user).first()
                if token:
                    token.delete()
                continue
            if key == 'facebook_account' and value:
                from api.serializers import FacebookAccountSerializer
                fb = FacebookAccountSerializer(data=value)
                if fb.is_valid():
                    fb.save()
                    value = fb.instance
                    fb_profile = getattr(fb.instance, 'profile', None)
                    if fb_profile and fb_profile != self:
                        fb.instance.profile.update(facebook_account=None)
                else:
                    continue
            if key in ['avatar', 'photo'] and value:
                if isinstance(value, list):
                    value = value[0]
                import uuid
                ext = value.content_type.split('/')[-1]
                filename = uuid.uuid4().hex
                value.name = f'{filename}.{ext}'
            setattr(self, key, value)
            if key == 'email' and value:
                self.send_confirmation_email()
        self.save()
        return self

    def send_confirmation_email(self):
        code = self.token(new=True)[6:]
        print('send', self.email, code)
        letter = {
            'theme': 'Подтверждение адреса электронной почты',
            'body': f'Для подтверждения адреса электронной почты для аккаунта {self.username} перейди по ссылке: '
                    f'https://dayspick.ru/confirm/?user={self.username}&code={code}',
            'to': self.email
        }
        Mail.send(**letter)
        print(f'https://dayspick.ru/confirm/?user={self.username}&code={code}')

    def confirm_email(self, code):
        if code == self.token()[6:]:
            self.update(email_confirm=self.email, email=None)
            self.token(new=True)
            return True
        return False

    def send_recovery_email(self):
        code = self.token(new=True)[6:]
        letter = {
            'theme': 'Восстановление доступа к аккаунту',
            'body': f'Для восстановления досутпа к аккаунту {self.username} перейди по ссылке: '
                    f'https://dayspick.ru/recovery/?user={self.username}&code={code}&to=settings',
            'to': self.email_confirm
        }
        Mail.send(**letter)
        print(f'https://dayspick.ru/recovery/?user={self.username}&code={code}&to=settings')

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.username


class UserProfileQuerySet(models.QuerySet):
    def search(self, **kwargs):
        users = self.exclude(account__isnull=True).exclude(account__is_public=False).order_by('-account__raised')

        if not kwargs:
            return users

        if kwargs.get('asker'):
            users = users.annotate(is_favorite=Case(
                When(favorite_of__profile=kwargs['asker'], then=True),
                default=False,
                output_field=BooleanField()
            )).order_by('-is_favorite')

        if kwargs.get('exclude'):
            pk = kwargs['exclude']
            users = users.exclude(pk=pk)

        if kwargs.get('tags'):
            users = users.filter(tags__tag_id__in=kwargs['tags'])

        if kwargs.get('filter'):
            search = kwargs['filter']
            if isinstance(search, list):
                search = search[0]
            words = search.split(' ')
            if len(words) == 1 and not words[0]:
                return []
            try:
                spelled = YandexSpeller().spelled(search)
            except:
                spelled = search
            options = [option for option in spelled.split(' ') if len(option) > 1]
            digits = ''.join(re.findall('[0-9]', search))
            phone_templates = [match.group(1) for match in re.finditer(r'(?=(\d{9}))', digits)] or ['-']

            phone_endswith = users.filter(
                reduce(lambda q, value: q | Q(account__phone_confirm__endswith=value), phone_templates, Q())
            )

            phone_contains = users.filter(
                reduce(lambda q, value: q | Q(account__phone_confirm__icontains=value), phone_templates, Q())
            )

            name_exact = users.filter(
                Q(account__user__username__iexact=search) |
                Q(first_name__iexact=search) |
                Q(last_name__iexact=search) |
                Q(account__user__username__iexact=spelled) |
                Q(first_name__iexact=spelled) |
                Q(last_name__iexact=spelled)
            )

            name_words = users.filter(
                Q(account__user__username__search=search) |
                Q(first_name__search=search) |
                Q(last_name__search=search) |
                Q(account__user__username__search=spelled) |
                Q(first_name__search=spelled) |
                Q(last_name__search=spelled)
            )

            name_contains = users.filter(
                Q(account__user__username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(account__user__username__in=words) |
                Q(first_name__in=words) |
                Q(last_name__in=words) |
                Q(account__user__username__icontains=spelled) |
                Q(first_name__icontains=spelled) |
                Q(last_name__icontains=spelled) |
                Q(account__user__username__in=options) |
                Q(first_name__in=options) |
                Q(last_name__in=options)
            )

            # tag_exact = users.filter(
            #     Q(tags__tag__title__iexact=search) |
            #     Q(tags__tag__title__iexact=spelled)
            # ).order_by('tags__rank')
            #
            # tag_words = users.filter(
            #     Q(tags__tag__title__search=search) |
            #     Q(tags__tag__title__search=spelled)
            # ).order_by('tags__rank')
            #
            # tag_contains = users.filter(
            #     Q(tags__tag__title__icontains=search) |
            #     Q(tags__tag__title__icontains=spelled)
            # ).order_by('tags__rank')

            info_contains = users.filter(
                Q(info__icontains=search) |
                Q(info__icontains=spelled)
            ).order_by('tags__rank')

            # users = name_exact | phone_endswith | tag_exact | name_words | tag_words | name_contains | tag_contains | info_contains | phone_contains
            users = name_exact | phone_endswith | name_words | name_contains | info_contains | phone_contains

        if kwargs.get('days'):
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            busy_users = users.filter(all_projects__days__date__in=dates, all_projects__is_wait=False).values('pk')
            users = users.exclude(pk__in=busy_users)
        return users.distinct()


class UserProfileManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        return UserProfileQuerySet(self.model, using=self._db)


class UserProfile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.SET_NULL, related_name='profile', null=True)
    first_name = models.CharField(max_length=64, **null)
    last_name = models.CharField(max_length=64, **null)
    email = models.EmailField(**null)
    phone = models.CharField(max_length=32, **null)
    telegram = models.CharField(max_length=32, **null)
    avatar = models.ImageField(upload_to='avatars', **null)
    photo = models.ImageField(upload_to='photos', **null)
    info = models.TextField(**null)

    objects = UserProfileManager()

    @property
    def is_deleted(self):
        return not bool(self.account)

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
        if not self.account:
            return '<DELETED>'
        return self.account.username

    def projects(self, asker=None):
        if not asker:
            asker = self
        projects = Project.objects.exclude(creator__isnull=True).filter(
            Q(user=self) | Q(children__user=self)).distinct().exclude(canceled=asker)
        if asker == self:
            projects = projects
        else:
            projects = projects.filter(creator=asker)
        return projects

    def offers(self):
        return self.created_projects.exclude(user=self).exclude(canceled=self)

    @property
    def days_off_project(self):
        return self.all_projects.get_or_create(creator__isnull=True)[0]

    @classmethod
    def get(cls, username, alt=None):
        account = Account.get(username)
        if account:
            return account.profile
        return alt

    def get_actual_projects(self, asker):
        if asker == self:
            return self.projects(asker).actual().reverse()
        if not asker:
            return Project.objects.none()
        return self.projects(asker).filter(creator=asker).actual().reverse()

    def get_actual_offers(self):
        return self.offers().actual().reverse()

    def get_calendar(self, asker=None, start=None, end=None, project_id=0, offers=False):
        if not start:
            start = datetime.now().date()
            start = start - timedelta(start.weekday() + 15 * 7)
        from api.serializers import CalendarDaySerializer
        if offers:
            all_days = Day.objects.filter(project__creator=self).exclude(project__user=self)
        else:
            all_days = Day.objects.filter(project__user=self).exclude(project__canceled__isnull=False)
        all_days = all_days.exclude(project__canceled=self).exclude(project_id=project_id)

        if start and end:
            all_days = all_days.filter(date__range=[start, end])
        elif start:
            all_days = all_days.filter(date__gte=start)
        elif end:
            all_days = all_days.filter(date__lte=end)

        if offers:
            return {
                'days': CalendarDaySerializer(all_days, many=True).dict()
            }

        if not asker:
            days_off = all_days.exclude(project__is_wait=True)
            days = {}
        else:
            if asker == self:
                days_off = all_days.exclude(project__creator__isnull=False)
                days = all_days.filter(project__creator__isnull=False).exclude(
                    project__canceled=self)
            else:
                days_off = all_days.exclude(project__creator=asker).exclude(project__is_wait=True)
                days = all_days.filter(project__creator=asker).exclude(
                    project__canceled=asker)
            days = CalendarDaySerializer(days, many=True).dict()

        return {
            'days': days,
            'daysOff': days_off.dates('date', 'day')
        }

    def page(self, asker, start=None, end=None):
        from api.serializers import ProfileSerializer, ProjectListItemSerializer
        projects = self.get_actual_projects(asker)
        result = {
            'id': self.id,
            'username': self.username,
            'profile': ProfileSerializer(self).data,
            'projects': ProjectListItemSerializer(projects, many=True, asker=asker).data,
            'calendar': self.get_calendar(asker, start, end),
            'tab': 'projects' if len(projects) or asker == self else 'profile',
            'is_self': self == asker,
            'unconfirmed_projects': projects.filter(confirmed=False).count() if asker == self else 0
        }
        return result

    def create_project(self, data):
        from api.serializers import ProjectSerializer, ProfileItemSerializer
        data['creator'] = ProfileItemSerializer(self).data
        serializer = ProjectSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            project = serializer.instance
            if not project.is_self:
                from api.bot import BotNotification
                BotNotification.create_project(project)
            return project
        print(serializer.errors)
        return {'error': 'Ошибка сохранения проекта'}

    def update_project(self, pk, data):
        from api.serializers import ProjectSerializer
        project = Project.objects.filter(pk=pk).first()
        if not project:
            return {'error': 'Проект не найден'}
        serializer = ProjectSerializer(instance=project, data=data, partial=True)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            project = serializer.instance
            if not project.is_self:
                from api.bot import BotNotification
                if project.creator == self:
                    BotNotification.update_project(project)
                if project.user == self:
                    BotNotification.accept_project(project)
            return serializer.instance
        print(serializer.errors)
        return {'error': 'Ошибка сохранения проекта'}

    def delete_project(self, pk):
        project = Project.objects.filter(pk=pk).first()
        if not project:
            return {'error': 'Проект не найден'}
        if not project.is_self and not project.canceled:
            project.canceled = self
            project.confirmed = False
            project.is_wait = True
            project.save()
            from api.bot import BotNotification
            if project.creator == self:
                BotNotification.cancel_project(project)
            elif project.user == self:
                BotNotification.decline_project(project)
        else:
            project.delete()
        return {}

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key in ['avatar', 'photo'] and value:
                if isinstance(value, list):
                    value = value[0]
                import uuid
                ext = value.content_type.split('/')[-1]
                filename = uuid.uuid4().hex
                value.name = f'{filename}.{ext}'
            setattr(self, key, value)
        return self.test_save()

    def test_save(self, last_key=None, last_value=None):
        try:
            self.save()
            return self
        except Exception as error:
            m = re.search(r'Key\s\((.+)\)=\((.+)\)', error.args[0])
            key, value = m.group(1), m.group(2)
            if key == last_key or value == last_value:
                raise OperationalError()
            UserProfile.objects.get(**{f'{key}': value}).update(**{f'{key}': None})
            return self.test_save(key, value)

    def __str__(self):
        return self.username

    def __repr__(self):
        return self.username


class Client(models.Model):
    class Meta:
        ordering = ['company', 'name']

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=64)
    company = models.CharField(max_length=64, **null, default='')

    objects = ClientsManager()

    @property
    def projects_list(self):
        return self.projects.without_folders()

    @property
    def full_name(self):
        full_name = self.name
        if self.company:
            full_name += f' ({self.company})'
        return full_name

    def __str__(self):
        return self.full_name


class ProjectsQuerySet(models.QuerySet):

    def without_children(self):
        return self.filter(parent__isnull=True)

    def folders(self):
        return self.filter(is_series=True).distinct()

    def without_folders(self):
        return self.filter(is_series=False).distinct()

    def actual(self):
        today = timezone.now().date()
        return self.without_folders().filter(Q(date_end__gte=today) | Q(is_paid=False)).distinct()

    def search(self, folders=False, without_folders=False, **kwargs):
        search = kwargs.get('filter')
        days = kwargs.get('days')

        if folders:
            projects = self.folders()
        elif search or days or without_folders:
            projects = self
        else:
            projects = self.exclude(Q(parent__isnull=False) & Q(creator=F('user'))).without_children()

        if search:
            if isinstance(search, list):
                search = search[0]
            try:
                spelled = YandexSpeller().spelled(search)
            except:
                spelled = search
            options = [option for option in spelled.split(' ') if len(option) > 1]
            vector = SearchVector('title', 'client__name', 'client__company')
            projects = projects.filter(
                Q(title__icontains=search) |
                Q(client__name__icontains=search) |
                Q(client__company__icontains=search) |
                Q(parent__title__icontains=search) |
                Q(title__icontains=spelled) |
                Q(client__name__icontains=spelled) |
                Q(client__company__icontains=spelled) |
                Q(parent__title__icontains=spelled) |
                Q(title__in=options) |
                Q(client__name__in=options) |
                Q(client__company__in=options) |
                Q(parent__title__in=options)
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

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='all_projects', **null)
    creator = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, related_name='created_projects', **null)
    date_start = models.DateField(**null)
    date_end = models.DateField(**null)
    title = models.CharField(max_length=64, **null)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, **null, related_name='projects')
    money = models.IntegerField(**null)
    money_per_day = models.FloatField(**null)
    money_calculating = models.BooleanField(default=False)
    info = models.TextField(**null)
    is_paid = models.BooleanField(default=False)
    is_wait = models.BooleanField(default=False)

    canceled = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, related_name='canceled_projects', **null)
    confirmed = models.BooleanField(default=True)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children', null=True, blank=True)

    is_series = models.BooleanField(default=False)

    objects = ProjectsManager()

    def set_days(self, days):
        self.days.set([Day.objects.get_or_create(project=self, **day)[0] for day in days])
        Day.objects.filter(project__isnull=True).delete()
        if self.days.count():
            self.date_start = self.days.first().date
            self.date_end = self.days.last().date
        else:
            self.date_start = None
            self.date_end = None

    @property
    def is_self(self):
        return self.creator == self.user

    @property
    def dates(self):
        return [i.date for i in self.days.all()]

    def child_delete(self, child):
        self.children.remove(child)
        if self.children.count() == 0:
            self.delete()
        else:
            self.parent_days_set()

    def parent_days_set(self):
        days = [day.date for day in Day.objects.filter(project__parent=self)]
        self.date_start = days[0]
        self.date_end = days[-1]
        self.save()

    @classmethod
    def get(cls, data):
        if isinstance(data, str) and data.isdigit():
            data = int(data)
        if isinstance(data, int):
            return cls.objects.filter(pk=data).first()
        if isinstance(data, dict):
            return cls.objects.filter(**data).first()
        return None

    def update(self, **data):
        for key, value in data.items():
            try:
                if key == 'days':
                    self.set_days(value)
                else:
                    setattr(self, key, value)
            except AttributeError as error:
                print(error)
            self.save()

    def get_title(self):
        if not self.creator:
            return '*days_off*'

        title = self.title or ''
        if not title:
            start = self.date_start.strftime('%d.%m.%y')
            end = self.date_end.strftime('%d.%m.%y')
            title = start
            if end != start:
                title += ' - ' + end
        if self.parent:
            title = self.parent.title + ' / ' + title

        return title

    def page(self, asker):
        if (self.user and self.user != asker and self.creator != asker) or self.canceled == asker:
            return {'error': 'Ошибка загрузки проекта'}
        from api.serializers import ProjectSerializer
        result = {
            'project': ProjectSerializer(self, asker=asker).data,
            'calendar': {
                'daysPick': self.dates
            }
        }

        user = None
        if self.user:
            user = self.user
        elif self.creator != asker:
            user = asker
        if user:
            date_start = self.date_start or timezone.now()
            start = date_start - timedelta(days=date_start.weekday(), weeks=15)
            end = start + timedelta(weeks=68)
            result['calendar'].update(user.get_calendar(asker, start, end, project_id=self.id))
        return result

    def __str__(self):
        return self.get_title()


class Day(models.Model):
    class Meta:
        ordering = ['date', 'project__date_start', 'project__date_end']

    date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='days', null=True)
    info = models.TextField(**null)

    def __str__(self):
        return ' - '.join([str(self.project), str(self.date)])


class FacebookAccount(models.Model):
    id = models.CharField(max_length=64, unique=True, primary_key=True)
    name = models.CharField(max_length=64, **null)
    picture = models.URLField(**null)

    def __str__(self):
        return f'{self.name} ({self.id})'


class ProjectShowing(models.Model):
    class Meta:
        ordering = ['project', 'time']

    project = models.ForeignKey('Project', related_name='responses', on_delete=models.CASCADE)
    user = models.ForeignKey('UserProfile', related_name='responses', on_delete=models.CASCADE, **null)
    response = models.BooleanField(default=False)
    comment = models.TextField(**null)
    time = models.DateTimeField(auto_now_add=True)
