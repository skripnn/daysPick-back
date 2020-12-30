# Generated by Django 3.1.1 on 2020-11-30 07:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0025_remove_day_user'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='day',
            options={'ordering': ['date', 'project']},
        ),
        migrations.AlterField(
            model_name='day',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='days', to='api.project'),
        ),
    ]
