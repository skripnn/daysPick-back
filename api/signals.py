import os

from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from .models import UserProfile


@receiver(models.signals.post_save, sender=UserProfile)
def profile_post_save(sender, instance, **kwargs):
    if not instance.is_confirmed and not instance.is_deleted:
        from .tasks import check_user_confirmation
        check_user_confirmation.apply_async((instance.username, ), countdown=30 * 60)


@receiver(models.signals.pre_save, sender=UserProfile)
def profile_pre_save(sender, instance, **kwargs):
    if not instance.phone_confirm:
        instance.is_public = False


@receiver(models.signals.pre_save, sender=UserProfile)
def auto_delete_file_on_change(sender, instance, **kwargs):

    def deleting(old_file, new_file):
        if old_file and old_file != new_file:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)

    if not instance.pk:
        return False

    try:
        profile = UserProfile.objects.get(pk=instance.pk)
    except UserProfile.DoesNotExist:
        return False

    deleting(profile.avatar or None, instance.avatar)
    deleting(profile.photo or None, instance.photo)


@receiver(models.signals.post_delete, sender=UserProfile)
def auto_delete_file_on_delete(sender, instance, **kwargs):

    def deleting(obj):
        if obj and os.path.isfile(obj.path):
            os.remove(instance.avatar.path)

    deleting(instance.avatar)
    deleting(instance.photo)


@receiver(models.signals.post_delete, sender=UserProfile)
def auto_delete_user(sender, instance, **kwargs):
    instance.user.delete()
