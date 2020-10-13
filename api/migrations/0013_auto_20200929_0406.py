# Generated by Django 3.1.1 on 2020-09-29 04:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0012_auto_20200928_1721'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='status',
            field=models.CharField(default='ok', max_length=16),
        ),
        migrations.AlterField(
            model_name='userdaysoff',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='days_off', to=settings.AUTH_USER_MODEL),
        ),
    ]
