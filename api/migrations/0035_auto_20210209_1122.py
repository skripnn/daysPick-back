# Generated by Django 3.1.1 on 2021-02-09 11:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0034_project_money_calculating'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='project',
            options={'ordering': ['-date_end', '-date_start']},
        ),
        migrations.RemoveField(
            model_name='project',
            name='dates',
        ),
    ]