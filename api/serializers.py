from rest_framework import serializers
from api.models import Project, Day, Client, UserProfile


def update_data(instance, validated_data, fields: list or str):
    if isinstance(fields, str):
        fields = [fields]
    for field in fields:
        value = validated_data.get(field, getattr(instance, field))
        setattr(instance, field, value)


class ProfileSelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['id', 'user']

    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    positions = serializers.StringRelatedField(many=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['id', 'user']

    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    positions = serializers.StringRelatedField(many=True)


class ClientProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'projects']
        read_only_fields = ['id']

    projects = ClientProjectSerializer(many=True, read_only=True)


class ClientShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'fullname']
        read_only_fields = ['id', 'fullname']

    fullname = serializers.SerializerMethodField('get_full_name')

    def get_full_name(self, client):
        fullname = client.name
        if client.company:
            fullname += f' ({client.company})'
        return fullname

    def create(self, validated_data):
        return Client.objects.create(**validated_data)


class ProjectShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title', 'client', 'money', 'is_paid']
        read_only_fields = ['id']

    client = ClientShortSerializer()


class ListProjectDaySerializer(serializers.ListSerializer):
    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)

    def to_representation(self, data):
        def transform(day):
            date = day.pop('date')
            if len(day) == 1:
                return date, list(day.values())[0]
            return date, day

        data = super().to_representation(data)
        return dict(transform(day) for day in data)

    def to_internal_value(self, data):
        def transform(key, value):
            day = {
                'date': key,
                'info': value
            }
            return day

        data = [transform(key, value) for key, value in data.items()]
        return super().to_internal_value(data)


class ProjectDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Day
        exclude = ['id', 'project']
        list_serializer_class = ListProjectDaySerializer


class ListCalendarDaySerializer(serializers.ListSerializer):
    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)

    def dict(self):
        days = {}
        for day in self.data:
            date = day.pop('date')
            if date not in days:
                days[date] = []
            days[date].append(day)
        return days


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Day
        exclude = ['id']
        list_serializer_class = ListCalendarDaySerializer

    project = ProjectShortSerializer()

    def dict(self):
        """this method works only with many=True"""
        pass


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        read_only_fields = ['id', 'date_start', 'date_end']
        fields = '__all__'

    days = ProjectDaySerializer(many=True, allow_null=True, default=None)
    client = ClientShortSerializer(allow_null=True)
    user = serializers.CharField()
    creator = serializers.CharField(write_only=True, allow_null=True)

    def create(self, validated_data):
        validated_data['user'] = UserProfile.get(validated_data['user'])
        validated_data['creator'] = UserProfile.get(validated_data['creator'])
        if validated_data.get('client'):
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
        if validated_data.get('client'):
            validated_data['client'] = Client.objects.get(user=instance.user, **validated_data['client'])
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


