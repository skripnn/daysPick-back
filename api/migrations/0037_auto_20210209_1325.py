# Generated by Django 3.1.1 on 2021-02-09 13:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0036_remove_userprofile_days_off'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='first_name',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_name',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='client',
            name='company',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
