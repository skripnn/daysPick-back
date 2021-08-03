import re
import uuid
from datetime import datetime, timedelta
from functools import reduce

from django.contrib.auth.models import User, AbstractUser
from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models, OperationalError
from django.db.models import Q, Count
from django.utils import timezone
from pyaspeller import YandexSpeller

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
        tags = cls.objects.all()

        if profile:
            tags = cls.objects.exclude(profile_tags__user=profile)

        if search:
            if isinstance(search, list):
                search = search[0]
            spelled = YandexSpeller().spelled(search)

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


class Contacts(models.Model):
    user = models.OneToOneField('UserProfile', on_delete=models.CASCADE, related_name='contacts')
    email = models.EmailField(**null)
    phone = models.CharField(max_length=32, **null)
    telegram = models.CharField(max_length=32, **null)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.save()
        return self


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='profile', null=True)
    first_name = models.CharField(max_length=64, **null)
    last_name = models.CharField(max_length=64, **null)
    email = models.EmailField(**null)
    email_confirm = models.EmailField(**null, unique=True)
    phone = models.CharField(max_length=32, **null)
    phone_confirm = models.CharField(max_length=32, **null, unique=True)
    telegram_chat_id = models.IntegerField(**null, unique=True)
    facebook_account = models.OneToOneField('FacebookAccount', on_delete=models.SET_NULL, **null, related_name='profile')
    is_public = models.BooleanField(default=False)
    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars', **null)
    photo = models.ImageField(upload_to='photos', **null)
    raised = models.DateTimeField(default=timezone.now)

    def delete(self, using=None, keep_parents=False):
        fields = self._meta.fields
        for f in fields:
            if f.null:
                if f.one_to_one:
                    related_field = getattr(self, f.name)
                    if related_field:
                        related_field.delete()
                setattr(self, f.name, None)
            elif f.has_default():
                if callable(f.default):
                    default = f.default()
                else:
                    default = f.default
                setattr(self, f.name, default)
        self.tags.all().delete()
        self.clients.all().delete()
        self.all_projects.filter(creator=self, user=self).delete()
        self.days_off_project.delete()
        self.save()

    @property
    def is_deleted(self):
        return not bool(self.user)

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
        if not self.user:
            return '<DELETED>'
        return self.user.username

    def projects(self, asker=None):
        if not asker:
            asker = self
        return self.all_projects.exclude(creator__isnull=True).exclude(canceled=asker)

    def offers(self):
        return self.created_projects.exclude(user=self).exclude(canceled=self)

    @property
    def days_off_project(self):
        return self.all_projects.get_or_create(creator__isnull=True)[0]

    @classmethod
    def create(cls, **kwargs):
        username = kwargs.pop('username', f'u{uuid.uuid4().hex[:16]}')
        password = kwargs.pop('password', uuid.uuid4().hex)
        password2 = kwargs.pop('password2', None)
        from django.db import IntegrityError
        try:
            profile = cls.objects.create(user=User.objects.create_user(username=username, password=password), **kwargs)
            Contacts.objects.create(user=profile)
            from api.bot import admins_notification
            admins_notification(f'Новый пользователь зарегистрирован.\nusername: {username}')
            if profile and profile.email:
                profile.send_confirmation_email()
        except IntegrityError as error:
            user = User.objects.filter(username=username).first()
            if user:
                user.delete()
            m = re.search(r'Key\s\((.+)\)=\((.+)\)', error.args[0])
            key, value = m.group(1), m.group(2)
            profile = cls.objects.get(**{f'{key}': value})
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
        return cls.objects.exclude(user__isnull=True).filter(user__username=username).first() or alt

    @classmethod
    def search(cls, **kwargs):
        users = cls.objects.exclude(is_public=False).order_by('-raised')
        if kwargs.get('filter'):
            search = kwargs['filter']
            if isinstance(search, list):
                search = search[0]
            words = search.split(' ')
            if len(words) == 1 and not words[0]:
                return []
            spelled = YandexSpeller().spelled(search)
            options = [option for option in spelled.split(' ') if len(option) > 1]
            digits = ''.join(re.findall('[0-9]', search))
            phone_templates = [match.group(1) for match in re.finditer(r'(?=(\d{9}))', digits)] or ['-']

            phone_endswith = users.filter(
                reduce(lambda q, value: q | Q(phone_confirm__endswith=value), phone_templates, Q())
            )

            phone_contains = users.filter(
                reduce(lambda q, value: q | Q(phone_confirm__icontains=value), phone_templates, Q())
            )

            name_exact = users.filter(
                Q(user__username__iexact=search) |
                Q(first_name__iexact=search) |
                Q(last_name__iexact=search) |
                Q(user__username__iexact=spelled) |
                Q(first_name__iexact=spelled) |
                Q(last_name__iexact=spelled)
            )

            name_words = users.filter(
                Q(user__username__search=search) |
                Q(first_name__search=search) |
                Q(last_name__search=search) |
                Q(user__username__search=spelled) |
                Q(first_name__search=spelled) |
                Q(last_name__search=spelled)
            )

            name_contains = users.filter(
                Q(user__username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(user__username__in=words) |
                Q(first_name__in=words) |
                Q(last_name__in=words) |
                Q(user__username__icontains=spelled) |
                Q(first_name__icontains=spelled) |
                Q(last_name__icontains=spelled) |
                Q(user__username__in=options) |
                Q(first_name__in=options) |
                Q(last_name__in=options)
            )

            tag_exact = users.filter(
                Q(tags__tag__title__iexact=search) |
                Q(tags__tag__title__iexact=spelled)
            ).order_by('tags__rank')

            tag_words = users.filter(
                Q(tags__tag__title__search=search) |
                Q(tags__tag__title__search=spelled)
            ).order_by('tags__rank')

            tag_contains = users.filter(
                Q(tags__tag__title__icontains=search) |
                Q(tags__tag__title__icontains=spelled)
            ).order_by('tags__rank')

            users = name_exact | phone_endswith | tag_exact | name_words | tag_words | name_contains | tag_contains | phone_contains

        if kwargs.get('days'):
            dates = [datetime.strptime(day, '%Y-%m-%d') for day in kwargs.get('days')]
            busy_users = users.filter(all_projects__days__date__in=dates, all_projects__is_wait=False).values('pk')
            users = users.exclude(pk__in=busy_users)
        return users.distinct()

    def token(self):
        from rest_framework.authtoken.models import Token
        token, created = Token.objects.get_or_create(user=self.user)
        return token.key

    def tg_code(self):
        return int(self.user.date_joined.timestamp()) + self.telegram_chat_id

    def get_actual_projects(self, asker):
        if asker == self:
            return self.projects(asker).actual().reverse()
        if not asker:
            return []
        return self.projects(asker).filter(creator=asker).actual().reverse()

    def get_actual_offers(self):
        return self.offers().actual().reverse()

    def get_calendar(self, asker=None, start=None, end=None, project_id=0, offers=False):
        from api.serializers import CalendarDaySerializer
        if offers:
            all_days = Day.objects.filter(project__creator=self).exclude(project__user=self)
        else:
            all_days = Day.objects.filter(project__user=self)
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

    def page(self, asker, token=False, additional=None):
        from api.serializers import ProjectSerializer, ProfileSerializer, ProfileSelfSerializer
        if asker == self:
            profile_serializer = ProfileSelfSerializer
        else:
            profile_serializer = ProfileSerializer
        start_date = datetime.now().date()
        start_date = start_date - timedelta(start_date.weekday() + 15 * 7)
        result = {
            'user': profile_serializer(self).data,
            'projects': ProjectSerializer(self.get_actual_projects(asker), many=True).data,
            'calendar': self.get_calendar(asker, start_date)
        }
        if asker == self:
            result['offers'] = ProjectSerializer(self.get_actual_offers(), many=True).data
            result['offersCalendar'] = self.get_calendar(start=start_date, offers=True)
        if token:
            result['token'] = self.token()
        if additional:
            result.update(additional)
        return result

    def update(self, **kwargs):
        for key, value in kwargs.items():
            try:
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
                if key == 'phone_confirm' and not self.phone_confirm:
                    self.is_public = True
                setattr(self, key, value)
                if key == 'email' and value:
                    self.send_confirmation_email()
            except AttributeError as error:
                print(error)
                if key == 'username' and value:
                    self.user.username = value
                    self.user.save()
                if key == 'password' and value:
                    self.user.set_password(value)
                    self.user.save()
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

    def __str__(self):
        return ' - '.join([str(self.user), f'{self.name} ({self.company})'])


class ProjectsQuerySet(models.QuerySet):
    def without_children(self):
        return self.filter(parent__isnull=True)

    def folders(self):
        return self.filter(children__isnull=False).distinct()

    def without_folders(self):
        return self.filter(children__isnull=True).distinct()

    def actual(self):
        today = timezone.now().date()
        return self.without_children().filter(Q(date_end__gte=today) | Q(is_paid=False)).filter(Q(children__isnull=True) | Q(children__is_paid=False)).distinct()

    def search(self, **kwargs):
        search = kwargs.get('filter')
        days = kwargs.get('days')
        folders = kwargs.get('folders')

        if folders:
            projects = self.folders()
        elif search or days:
            projects = self.without_folders()
        else:
            projects = self.without_children()

        if search:
            if isinstance(search, list):
                search = search[0]
            spelled = YandexSpeller().spelled(search)
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
    money_per_day = models.IntegerField(**null)
    money_calculating = models.BooleanField(default=False)
    info = models.TextField(**null)
    is_paid = models.BooleanField(default=False)
    is_wait = models.BooleanField(default=False)
    canceled = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, related_name='canceled_projects', **null)
    confirmed = models.BooleanField(default=True)
    parent = models.ForeignKey('self', **null, on_delete=models.CASCADE, related_name='children')

    objects = ProjectsManager()

    @property
    def dates(self):
        return [i.date for i in self.days.all()]

    @property
    def is_folder(self):
        return bool(self.children.count())

    def child_delete(self, child):
        self.children.remove(child)
        if self.children.count() == 0:
            self.delete()

    def parent_days_set(self):
        days = [day.date for day in Day.objects.filter(project__parent=self)]
        self.date_start = days[0]
        self.date_end = days[-1]
        self.save()

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


class FacebookAccount(models.Model):
    id = models.CharField(max_length=64, unique=True, primary_key=True)
    name = models.CharField(max_length=64, **null)
    picture = models.URLField(**null)

    def __str__(self):
        return f'{self.name } ({self.id})'
