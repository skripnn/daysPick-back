# Generated by Django 3.1.1 on 2021-08-17 09:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0113_delete_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='account',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profile', to='api.account'),
        ),
    ]
