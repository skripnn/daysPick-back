from django.contrib.auth.models import User
from rest_framework import serializers
from api.models import Project, Day, Client


def update_data(instance, validated_data, field):
    value = validated_data.get(field, getattr(instance, field))
    setattr(instance, field, value)


class UserProfileSerializer(serializers.Serializer):
    days_off = serializers.ListField(child=serializers.DateField(), allow_empty=True)

    def update(self, instance, validated_data):
        fields = ['days_off']
        for field in fields:
            update_data(instance, validated_data, field)

        instance.save()
        return instance


class UserSelfSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()
    daysOff = serializers.ListField(child=serializers.DateField(), allow_empty=True, source='profile.days_off')


class UserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()


class DaySerializer(serializers.Serializer):
    date = serializers.DateField()


class ClientSerializer(serializers.Serializer):
    name = serializers.CharField()
    company = serializers.CharField(allow_blank=True)
    fullname = serializers.SerializerMethodField('get_full_name')

    def get_full_name(self, client):
        fullname = client.name
        if client.company:
            fullname += f' ({client.company})'
        return fullname

    def create(self, validated_data):
        return Client.objects.create(**validated_data)


class ProjectShortSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = ClientSerializer()
    money = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    is_paid = serializers.BooleanField()


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = ClientSerializer(allow_null=True)
    money = serializers.IntegerField(allow_null=True)
    info = serializers.CharField(allow_blank=True)
    status = serializers.CharField(default='ok')
    is_paid = serializers.BooleanField()
    creator = serializers.CharField()
    user = serializers.CharField()
    days = DaySerializer(many=True, allow_null=True, default=None)

    def create(self, validated_data):
        validated_data['user'] = User.objects.get(username=validated_data['user'])
        validated_data['creator'] = User.objects.get(username=validated_data['creator'])
        validated_data['date_start'] = validated_data['dates'][0]
        validated_data['date_end'] = validated_data['dates'][-1]
        if validated_data['client']:
            validated_data['client'] = Client.objects.get(user=validated_data['creator'], **validated_data['client'])
        days = validated_data.pop('days')
        project = Project.objects.create(**validated_data)
        for day in days:
            Day.objects.create(project=project, **day)
        return project

    def update(self, instance, validated_data):
        fields = ['dates', 'title', 'money', 'info', 'status', 'is_paid']
        days = validated_data.pop('days')
        instance.days.exclude(date__in=[day['date'] for day in days]).delete()
        validated_data['days'] = [Day.objects.get_or_create(project=instance, **day) for day in days]
        validated_data['client'] = Client.objects.get(user__username=validated_data['creator'], **validated_data['client'])
        for field in fields:
            update_data(instance, validated_data, field)
        instance.date_start = instance.dates[0]
        instance.date_end = instance.dates[-1]
        instance.save()
        return instance


