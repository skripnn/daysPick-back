# Generated by Django 3.1.1 on 2021-09-16 01:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0116_delete_contacts'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='is_series',
            field=models.BooleanField(default=False),
        ),
    ]
