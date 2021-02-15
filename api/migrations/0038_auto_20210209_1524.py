# Generated by Django 3.1.1 on 2021-02-09 15:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0037_auto_20210209_1325'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clients', to='api.userprofile'),
        ),
        migrations.AddField(
            model_name='project',
            name='profile',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='projects', to='api.userprofile'),
        ),
    ]