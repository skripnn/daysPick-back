# Generated by Django 3.1.1 on 2021-02-08 18:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0032_auto_20210207_1238'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='money_per_day',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]