# Generated by Django 3.1.1 on 2020-09-11 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='money',
            field=models.IntegerField(blank=True),
        ),
    ]
