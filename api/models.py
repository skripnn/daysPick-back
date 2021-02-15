from django.contrib.auth.models import User, AbstractUser
from django.contrib.postgres.search import SearchRank, SearchVector
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

null = {'null': True, 'blank': True}


class ClientsManager(models.Manager):
    use_for_related_fields = True

    def search(self, search=None):
        if not search:
            return self.get_queryset().all()

        vector = SearchVector('name', 'company')
        return self.get_queryset().filter(Q(name__icontains=search) | Q(company__icontains=search))\
            .annotate(rank=SearchRank(vector, search)).order_by('-rank')


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
    is_confirmed = models.BooleanField(default=False)
    first_name = models.CharField(max_length=64, **null)
    last_name = models.CharField(max_length=64, **null)
    positions = models.ManyToManyField('Position', related_name='profiles')

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
        return cls.objects.filter(user__username=username).first() or alt

    def get_actual_projects(self, asker):
        today = timezone.now().date()
        if asker == self:
            return self.projects.filter(Q(date_end__gte=today) | Q(is_paid=False))
        if not asker:
            return None
        return self.projects.filter(creator=asker)

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            profile = UserProfile.objects.create(user=instance)
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
        return self.filter(Q(title__icontains=search) | Q(client__name__icontains=search) | Q(client__company__icontains=search))\
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
