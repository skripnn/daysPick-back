# Generated by Django 3.1.1 on 2021-03-22 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0079_userprofile_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='facebook_id',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]