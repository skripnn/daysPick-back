# Generated by Django 3.1.1 on 2021-09-29 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0118_account_favorites'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='telegram_notifications',
            field=models.BooleanField(default=False),
        ),
    ]
