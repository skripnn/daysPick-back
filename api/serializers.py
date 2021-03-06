import datetime

from django.utils import timezone
from rest_framework import serializers

from api.models import Project, Day, Client, UserProfile, Tag, FacebookAccount


def update_data(instance, validated_data, fields: list or str):
    if isinstance(fields, str):
        fields = [fields]
    for field in fields:
        value = validated_data.get(field, getattr(instance, field))
        setattr(instance, field, value)


class FacebookAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacebookAccount
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        if kwargs.get('data'):
            if isinstance(kwargs['data']['picture'], dict):
                kwargs['data']['picture'] = kwargs['data']['picture']['data'].get('url')
        super().__init__(*args, **kwargs)
        if not self.instance and getattr(self, 'initial_data', None):
            self.instance = FacebookAccount.objects.filter(id=self.initial_data['id']).first()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        read_only_fields = ['id']
        fields = ['id', 'title']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['id', 'user', 'raised']
        read_only_fields = ['get_can_be_raised']

    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    facebook_account = FacebookAccountSerializer(allow_null=True)

    def to_representation(self, obj):
        ret = super().to_representation(obj)

        tags = obj.tags.list()
        serializer = TagSerializer(tags, many=True)
        ret['tags'] = serializer.data

        return ret

    def page(self, asker, token=False):
        result = {
            'user': self.data,
            'projects': ProjectSerializer(self.instance.get_actual_projects(asker), many=True).data
        }
        if token:
            result['token'] = self.instance.token()
        return result


class ProfileSelfSerializer(ProfileSerializer):
    can_be_raised = serializers.SerializerMethodField('get_can_be_raised')

    def get_can_be_raised(self, instance):
        delta = timezone.now() - instance.raised
        return delta > datetime.timedelta(hours=3)


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
        return Client.objects.get_or_create(**validated_data)[0]


class ProjectShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title', 'client', 'money', 'is_paid', 'is_wait']

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


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        read_only_fields = ['id', 'date_start', 'date_end', 'parent_name', 'is_folder', 'children']
        fields = '__all__'

    days = ProjectDaySerializer(many=True, allow_null=True, default=None)
    client = ClientShortSerializer(allow_null=True, default=None)
    user = serializers.CharField()
    creator = serializers.CharField(allow_null=True)
    children = RecursiveField(many=True, allow_null=True, read_only=True)
    parent_name = serializers.SerializerMethodField('get_parent_name', allow_null=True)
    is_folder = serializers.BooleanField(read_only=True)
    parent = serializers.SerializerMethodField('get_parent', allow_null=True)

    def get_parent_name(self, obj):
        if not obj.parent:
            return None
        return obj.parent.title

    def get_parent(self, obj):
        if not obj.parent:
            return None
        return {'id': obj.parent.id, 'title': obj.parent.title}

    def create(self, validated_data):
        validated_data['user'] = UserProfile.get(validated_data['user'])
        validated_data['creator'] = UserProfile.get(validated_data['creator'])
        if validated_data.get('client'):
            validated_data['client'] = Client.objects.filter(**validated_data['client']).first()
        days = validated_data.pop('days')
        days.sort(key=lambda i: i['date'])
        validated_data['date_start'] = days[0]['date']
        validated_data['date_end'] = days[-1]['date']

        project = Project.objects.create(**validated_data)
        for day in days:
            project.days.create(**day)
        parent = self.parent_set(validated_data)
        if parent:
            parent.children.add(project)
            parent.parent_days_set()
        return project

    def update(self, instance, validated_data):
        if validated_data.get('user') and validated_data['user'] != instance.user.username:
            instance.canceled = instance.creator
            instance.is_wait = True
            instance.save()
            return self.create(validated_data)
        validated_data['user'] = UserProfile.get(validated_data['user'])
        validated_data['creator'] = UserProfile.get(validated_data['creator'])
        if validated_data.get('client'):
            validated_data['client'] = Client.objects.get(user=instance.user, **validated_data['client'])
        validated_data['parent'] = self.parent_set(validated_data, instance)
        fields = ['client', 'title', 'money', 'money_per_day', 'money_calculating', 'info', 'is_paid', 'is_wait', 'confirmed', 'parent']
        if validated_data.get('is_paid'):
            validated_data['is_wait'] = False
        update_data(instance, validated_data, fields)

        days = validated_data.pop('days')
        days.sort(key=lambda i: i['date'])
        instance.days.set([Day.objects.get_or_create(project=instance, **day)[0] for day in days])
        Day.objects.filter(project__isnull=True).delete()
        if instance.is_folder:
            days = [{'date': day.date} for day in Day.objects.filter(project__parent=instance)]
        instance.date_start = days[0]['date']
        instance.date_end = days[-1]['date']
        instance.save()
        if instance.parent:
            instance.parent.parent_days_set()
        return instance

    def parent_set(self, validated_data, instance=None):
        parent = self.initial_data.get('parent')
        if parent:
            if parent.get('id'):
                parent = Project.objects.filter(id=parent['id'], title=parent['title']).first()
            else:
                money_params = {'money_calculating': validated_data.get('money_calculating')}
                if money_params['money_calculating']:
                    money_params['money_per_day'] = validated_data.get('money_per_day')
                else:
                    money_params['money'] = validated_data.get('money')
                parent = Project.objects.create(
                    title=parent['title'],
                    user=validated_data['user'],
                    creator=validated_data['creator'],
                    client=validated_data['client'],
                    **money_params
                )
        if instance and instance.parent:
            if (parent and instance.parent.id != parent.id) or not parent:
                instance.parent.child_delete(instance)
        return parent


class ProjectChildSerializer(ProjectSerializer):
    pass


class UserPageSerializer(serializers.Serializer):

    def to_representation(self, obj):
        ret = super().to_representation(obj)
        ret['token'] = obj.token()
        ret['user'] = {
            'user': ProfileSelfSerializer(obj).data,
            'projects': ProjectSerializer(obj.get_actual_projects(obj), many=True).data
        }
        return ret
