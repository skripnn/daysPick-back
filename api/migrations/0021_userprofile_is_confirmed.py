# Generated by Django 3.1.1 on 2020-10-20 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0020_auto_20201020_1306'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_confirmed',
            field=models.BooleanField(default=False),
        ),
    ]
