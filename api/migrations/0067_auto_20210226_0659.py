# Generated by Django 3.1.1 on 2021-02-26 06:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0066_auto_20210226_0650'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rank', models.IntegerField(default=0)),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tag')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.userprofile')),
            ],
            options={
                'ordering': ['user', 'rank'],
            },
        ),
        migrations.AddField(
            model_name='userprofile',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='profiles', to='api.ProfileTag'),
        ),
    ]
