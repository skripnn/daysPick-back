# Generated by Django 3.1.1 on 2021-08-16 09:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0106_profiletag_profile'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profiletag',
            options={'ordering': ['profile', 'rank']},
        ),
        migrations.RemoveField(
            model_name='profiletag',
            name='user',
        ),
    ]
