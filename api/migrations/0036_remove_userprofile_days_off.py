# Generated by Django 3.1.1 on 2021-02-09 13:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0035_auto_20210209_1122'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='days_off',
        ),
    ]
