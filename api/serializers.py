from datetime import datetime

from django.contrib.auth.models import User
from rest_framework import serializers
from api.models import Project, Day


def update_data(instance, validated_data, field):
    value = validated_data.get(field, getattr(instance, field))
    setattr(instance, field, value)



class DaysField(serializers.SlugRelatedField):
    def to_internal_value(self, data):
        project = self.root.instance
        date = datetime.strptime(data, "%Y-%m-%d").date()
        i, create = Day.objects.get_or_create(date=date, project=project)
        return i


class ProjectShortSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = serializers.CharField()
    money = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    is_paid = serializers.BooleanField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = serializers.CharField()
    money = serializers.IntegerField(allow_null=True)
    info = serializers.CharField(allow_blank=True)
    status = serializers.CharField(default='ok')
    is_paid = serializers.BooleanField()
    creator = serializers.CharField()
    user = serializers.CharField()
    # days = DaysField(many=True, queryset=Day.objects.all(), slug_field='date', allow_null=True)

    def create(self, validated_data):
        validated_data['user'] = User.objects.get(username=validated_data['user'])
        validated_data['creator'] = User.objects.get(username=validated_data['creator'])
        validated_data['date_start'] = validated_data['dates'][0]
        validated_data['date_end'] = validated_data['dates'][-1]
        # days = validated_data.pop('days')
        project = Project.objects.create(**validated_data)
        # project.days.set(days)
        return project

    def update(self, instance, validated_data):
        fields = ['dates', 'title', 'money', 'client', 'info', 'status', 'is_paid']
        # instance.days.set(validated_data['days'])
        for field in fields:
            update_data(instance, validated_data, field)
        instance.date_start = instance.dates[0]
        instance.date_end = instance.dates[-1]
        instance.save()
        return instance


class UserProfileSerializer(serializers.Serializer):
    days_off = serializers.ListField(child=serializers.DateField(), allow_empty=True)

    def update(self, instance, validated_data):
        fields = ['days_off']
        for field in fields:
            update_data(instance, validated_data, field)

        instance.save()
        return instance


class UserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()
    daysOff = serializers.ListField(child=serializers.DateField(), allow_empty=True, source='profile.days_off')

