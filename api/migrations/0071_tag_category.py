# Generated by Django 3.1.1 on 2021-02-27 08:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0070_auto_20210226_1425'),
    ]

    operations = [
        migrations.AddField(
            model_name='tag',
            name='category',
            field=models.IntegerField(choices=[(0, ''), (1, 'Звук'), (2, 'Свет')], default=0),
        ),
    ]