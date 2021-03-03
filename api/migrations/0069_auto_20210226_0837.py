# Generated by Django 3.1.1 on 2021-02-26 08:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0068_remove_userprofile_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profiletag',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tags', to='api.userprofile'),
        ),
    ]