# Generated by Django 3.1.1 on 2021-02-09 15:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0039_auto_20210209_1539'),
    ]

    operations = [
        migrations.RenameField(
            model_name='client',
            old_name='profile',
            new_name='user',
        ),
        migrations.RenameField(
            model_name='project',
            old_name='profile',
            new_name='user',
        ),
    ]