# Generated by Django 3.1.1 on 2021-03-23 09:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0083_auto_20210322_1723'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacebookAccount',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(blank=True, max_length=64, null=True)),
                ('picture', models.URLField(blank=True, null=True)),
            ],
        ),
    ]
