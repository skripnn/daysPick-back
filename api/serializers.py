from django.contrib.auth.models import User
from rest_framework import serializers
from api.models import Project, Day, Client


def update_data(instance, validated_data, fields: list or str):
    if isinstance(fields, str):
        fields = [fields]
    for field in fields:
        value = validated_data.get(field, getattr(instance, field))
        setattr(instance, field, value)


# class UserProfileSerializer(serializers.Serializer):
#     days_off = serializers.ListField(child=serializers.DateField(), allow_empty=True)
#
#     def update(self, instance, validated_data):
#         fields = ['days_off']
#         update_data(instance, validated_data, fields)
#
#         instance.save()
#         return instance


class UserSelfSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()
    # daysOff = serializers.ListField(child=serializers.DateField(), allow_empty=True, source='profile.days_off')


class UserSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    username = serializers.CharField()


class ClientSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
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
    title = serializers.CharField(allow_blank=True)
    client = ClientSerializer()
    money = serializers.IntegerField(allow_null=True)
    is_paid = serializers.BooleanField()


class ListProjectDaySerializer(serializers.ListSerializer):
    def to_representation(self, data):
        data = super().to_representation(data)
        return {day['date']: day['info'] for day in data}


class ListCalendarDaySerializer(serializers.ListSerializer):
    def dict(self):
        days = {}
        for day in self.data:
            date = day.pop('date')
            if date not in days:
                days[date] = []
            days[date].append(day)
        return days


class CalendarDaySerializer(serializers.Serializer):
    class Meta:
        list_serializer_class = ListCalendarDaySerializer

    date = serializers.DateField()
    project = ProjectShortSerializer()
    info = serializers.CharField(allow_blank=True)

    def dict(self):
        """this method works only with many=True"""
        pass


class ProjectSerializer(serializers.Serializer):
    class DaySerializer(serializers.Serializer):
        class Meta:
            list_serializer_class = ListProjectDaySerializer

        date = serializers.DateField()
        info = serializers.CharField(allow_null=True, allow_blank=True)

    id = serializers.IntegerField(read_only=True)
    user = serializers.CharField()
    creator = serializers.CharField()
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True, read_only=True)
    date_start = serializers.DateField(allow_null=True, read_only=True)
    date_end = serializers.DateField(allow_null=True, read_only=True)
    days = DaySerializer(many=True, allow_null=True, default=None)
    title = serializers.CharField(allow_blank=True)
    client = ClientSerializer(allow_null=True)
    money = serializers.IntegerField(allow_null=True)
    money_per_day = serializers.IntegerField(allow_null=True)
    money_calculating = serializers.BooleanField()
    info = serializers.CharField(allow_blank=True)
    is_paid = serializers.BooleanField()

    def create(self, validated_data):
        validated_data['user'] = User.objects.get(username=validated_data['user'])
        if 'creator' in validated_data:
            validated_data['creator'] = User.objects.get(username=validated_data['creator'])
        if 'client' in validated_data:
            validated_data['client'] = Client.objects.get(user=validated_data['creator'], **validated_data['client'])
        days = validated_data.pop('days')
        days.sort(key=lambda i: i['date'])
        validated_data['date_start'] = days[0]['date']
        validated_data['date_end'] = days[-1]['date']
        project = Project.objects.create(**validated_data)
        for day in days:
            project.days.create(**day)
        return project

    def update(self, instance, validated_data):
        if 'client' in validated_data:
            validated_data['client'] = Client.objects.get(user__username=validated_data['user'], **validated_data['client'])
        fields = ['client', 'title', 'money', 'money_per_day', 'money_calculating', 'info', 'is_paid']
        update_data(instance, validated_data, fields)

        days = validated_data.pop('days')
        days.sort(key=lambda i: i['date'])
        instance.days.set([Day.objects.get_or_create(project=instance, **day)[0] for day in days])
        Day.objects.filter(project__isnull=True).delete()
        instance.date_start = days[0]['date']
        instance.date_end = days[-1]['date']
        instance.save()
        return instance


