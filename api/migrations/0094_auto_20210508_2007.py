# Generated by Django 3.1.1 on 2021-05-08 20:07

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0093_auto_20210508_1309'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='vk_account',
        ),
        migrations.DeleteModel(
            name='VkAccount',
        ),
    ]