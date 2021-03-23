# Generated by Django 3.1.1 on 2021-03-23 09:40

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0084_facebookaccount'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='facebook_account',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.facebookaccount'),
        ),
    ]
