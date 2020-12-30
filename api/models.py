from django.contrib.auth.models import User, AbstractUser
from django.db import models
from django.contrib.postgres import fields
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    days_off = fields.ArrayField(models.DateField(), blank=True, default=list)
    is_confirmed = models.BooleanField(default=False)

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


class Project(models.Model):
    class Meta:
        ordering = ['date_start', 'date_end']

    dates = fields.ArrayField(models.DateField(), null=True, blank=True)
    date_start = models.DateField(null=True)
    date_end = models.DateField(null=True)
    title = models.CharField(max_length=64, blank=True)
    client = models.CharField(max_length=64)
    money = models.IntegerField(blank=True, null=True)
    info = models.TextField(blank=True)
    status = models.CharField(max_length=16, default='ok')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                related_name='created_projects')
    is_paid = models.BooleanField(default=False)


class Day(models.Model):
    class Meta:
        ordering = ['date', 'project']

    date = models.DateField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='days')

    def __str__(self):
        return str(self.date) + ' - project ' + str(self.project_id)

    def __repr__(self):
        return self.date
