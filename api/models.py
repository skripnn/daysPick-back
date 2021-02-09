from django.contrib.auth.models import User, AbstractUser
from django.db import models
from django.contrib.postgres import fields
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    days_off = fields.ArrayField(models.DateField(), blank=True, default=list)
    is_confirmed = models.BooleanField(default=False)

    @property
    def days_off_project(self):
        return self.user.projects.filter(creator__isnull=True).first()

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            UserProfile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        if not instance.is_superuser:
            instance.profile.save()

    def __str__(self):
        return self.user.username


class Client(models.Model):
    class Meta:
        ordering = ['name', 'company']

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=64)
    company = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return ' - '.join([str(self.user), f'{self.name} ({self.company})'])


class Project(models.Model):
    class Meta:
        ordering = ['-date_end', '-date_start']

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='created_projects', null=True, blank=True)
    date_start = models.DateField(null=True, blank=True)
    date_end = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=64, null=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    money = models.IntegerField(null=True, blank=True)
    money_per_day = models.IntegerField(null=True, blank=True)
    money_calculating = models.BooleanField(default=False)
    info = models.TextField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)

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
    info = models.TextField(null=True, blank=True)

    def __str__(self):
        return ' - '.join([str(self.project), str(self.date)])
