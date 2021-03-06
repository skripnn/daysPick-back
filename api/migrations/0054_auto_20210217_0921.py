# Generated by Django 3.1.1 on 2021-02-17 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0053_auto_20210217_0917'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='email_confirm',
            field=models.EmailField(blank=True, max_length=254, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_confirm',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
    ]
