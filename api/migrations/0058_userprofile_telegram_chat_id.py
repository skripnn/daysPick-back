# Generated by Django 3.1.1 on 2021-02-17 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0057_telegram'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='telegram_chat_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
