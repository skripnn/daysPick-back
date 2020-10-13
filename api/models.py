from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres import fields


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    days_off = fields.ArrayField(models.DateField(), null=True, blank=True)


class Contact(models.Model):
    name = models.CharField(max_length=64)
    phone = models.CharField(max_length=32)


class Project(models.Model):
    dates = fields.ArrayField(models.DateField(), null=True, blank=True)
    title = models.CharField(max_length=64, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.SET_NULL, default=None, null=True, blank=True)
    money = models.IntegerField(blank=True, null=True)
    info = models.TextField(blank=True)
    status = models.CharField(max_length=16, default='ok')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, default=User.is_active, null=True,
                                related_name='created_projects')



