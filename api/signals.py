import os

from django.db import models
from django.dispatch import receiver

from .models import UserProfile, Account


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


@receiver(models.signals.pre_delete, sender=UserProfile)
def delete_account_and_user(sender, instance, **kwargs):
    if instance.account:
        instance.account.delete()


@receiver(models.signals.post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    if created:
        from api.bot import BotNotification
        BotNotification.send_to_admins(f'Аккаунт создан.\nusername: {instance.username}')
    if not instance.is_confirmed:
        from .tasks import check_user_confirmation
        try:
            check_user_confirmation.apply_async((instance.username, ), countdown=30 * 60)
        except Exception as e:
            print(e)


@receiver(models.signals.pre_save, sender=Account)
def account_pre_save(sender, instance, **kwargs):
    if not instance.is_confirmed:
        instance.is_public = False
    else:
        if instance.pk:
            pre_account = Account.objects.get(pk=instance.pk)
            if not pre_account.is_confirmed:
                instance.is_public = True
        else:
            if instance.is_confirmed:
                instance.is_public = True


@receiver(models.signals.pre_delete, sender=Account)
def account_pre_delete(sender, instance, **kwargs):
    try:
        instance.profile.update(photo=None, avatar=None)
    except:
        pass


@receiver(models.signals.post_delete, sender=Account)
def account_post_delete(sender, instance, **kwargs):
    from api.bot import BotNotification
    BotNotification.send_to_admins(f'Аккаунт удален.\nusername: {instance.username}')
    if instance.user:
        instance.user.delete()
