# Generated by Django 3.1.1 on 2021-02-27 13:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0072_auto_20210227_0859'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profiletag',
            name='tag',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='profile_tags', to='api.tag'),
        ),
    ]