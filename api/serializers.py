from rest_framework import serializers
from api.models import Project, Day, Client, UserProfile, Tag, FacebookAccount, Account


def update_data(instance, validated_data, fields: list or str):
    if isinstance(fields, str):
        fields = [fields]
    for field in fields:
        value = validated_data.get(field, getattr(instance, field))
        setattr(instance, field, value)


class RecursiveField(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data


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


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ...

    def to_internal_value(self, data):
        pk = None
        if isinstance(data, dict):
            pk = data.get('id')
        elif isinstance(data, int):
            pk = data
        if pk:
            return self.Meta.model.objects.filter(id=pk).first()
        return super().to_internal_value(data)


class ClientItemSerializer(ItemSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'full_name', 'company']
        read_only_fields = ['full_name']


class ProfileItemSerializer(ItemSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'username', 'full_name', 'avatar', 'is_simulated']

    def to_representation(self, obj):
        ret = super().to_representation(obj)

        tags = obj.tags.list()
        serializer = TagSerializer(tags, many=True)
        ret['tags'] = serializer.data

        return ret


class ProfileItemShortSerializer(ItemSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'full_name', 'avatar']


class ProjectShortSerializer(ItemSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title']


class ProjectShortGetTitleSerializer(ItemSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title']

    title = serializers.SerializerMethodField('get_title')
    def get_title(self, instance):
        return instance.get_title()


class ProfileShortSerializer(ItemSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'full_name']


class ClientShortSerializer(ItemSerializer):
    class Meta:
        model = Client
        fields = ['id', 'full_name', 'name']


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        exclude = ['id', 'account']

    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_public = serializers.SerializerMethodField('get_is_public', read_only=True)
    tags = serializers.SerializerMethodField('get_tags')
    is_simulated = serializers.BooleanField(read_only=True)

    @staticmethod
    def get_tags(instance):
        return TagSerializer(instance.tags.list(), many=True).data

    @staticmethod
    def get_is_public(instance):
        if instance.account:
            return instance.account.is_public
        return False


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ['user', 'raised']

    id = serializers.SerializerMethodField('get_profile_id', read_only=True)
    username = serializers.CharField(read_only=True)
    facebook_account = FacebookAccountSerializer(allow_null=True)
    is_confirmed = serializers.BooleanField(read_only=True)
    can_be_raised = serializers.BooleanField(read_only=True)
    profile = ProfileSerializer()
    unconfirmed_projects = serializers.SerializerMethodField('get_unconfirmed_projects')

    @staticmethod
    def get_profile_id(instance):
        return instance.profile.id

    @staticmethod
    def get_unconfirmed_projects(instance):
        return instance.profile.projects().filter(confirmed=False).count()


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'name', 'company', 'projects']
        read_only_fields = ['id', 'projects']

    projects = serializers.SerializerMethodField('get_projects', read_only=True)

    @staticmethod
    def get_projects(instance):
        return ProjectShortGetTitleSerializer(instance.projects.all().without_folders(), many=True, allow_null=True).data


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


class CalendarDayProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'title', 'is_wait']

    title = serializers.SerializerMethodField('get_title')

    def get_title(self, instance):
        return instance.get_title()


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Day
        exclude = ['id']
        list_serializer_class = ListCalendarDaySerializer

    project = CalendarDayProjectSerializer()

    def dict(self):
        """this method works only with many=True"""
        pass


class ProjectSerializerBase(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['id', 'date_start', 'date_end', 'children', 'response']

    def __init__(self, *args, asker=None, **kwargs):
        self.asker = asker
        super().__init__(*args, **kwargs)

    children = serializers.SerializerMethodField('get_children', allow_null=True, read_only=True)
    response = serializers.SerializerMethodField('get_response', allow_null=True, read_only=True)

    def get_children(self, instance):
        queryset = instance.children.all()
        if self.asker:
            queryset = queryset.exclude(canceled=self.asker)
            if self.asker != instance.creator:
                queryset = queryset.filter(user=self.asker)
        return ProjectListItemSerializer(queryset, many=True, allow_null=True, read_only=True).data

    def get_response(self, instance):
        if self.asker and not instance.is_series and not instance.user:
            response = instance.responses.filter(user=self.asker).first()
            if response:
                return response.response
        return None


class ProjectListItemSerializer(ProjectSerializerBase):
    class Meta:
        model = Project
        fields = ['id', 'title', 'client', 'creator', 'user', 'money', 'money_per_day', 'money_calculating', 'dates', 'date_start', 'date_end', 'parent', 'children', 'is_wait', 'is_paid', 'canceled', 'confirmed', 'is_series']

    client = ClientShortSerializer(allow_null=True)
    creator = ProfileShortSerializer()
    user = ProfileShortSerializer(allow_null=True)
    canceled = ProfileShortSerializer(allow_null=True)
    dates = serializers.SerializerMethodField('get_dates')
    parent = ProjectShortSerializer(allow_null=True)

    def get_dates(self, obj):
        return [i.date for i in obj.days.all()]


class ProjectSerializer(ProjectSerializerBase):

    days = ProjectDaySerializer(many=True, allow_null=True, default=None)
    client = ClientItemSerializer(allow_null=True, default=None)
    creator = ProfileItemShortSerializer()
    user = ProfileItemShortSerializer(allow_null=True, default=None)
    canceled = ProfileItemShortSerializer(allow_null=True, default=None)
    parent = ProjectShortSerializer(allow_null=True, default=None)

    def create(self, validated_data):
        days = validated_data.pop('days')
        project = super().create(validated_data)
        if days:
            project.update(days=days)

        return project

    def update(self, instance, validated_data):
        days = validated_data.pop('days', None)
        project = super().update(instance, validated_data)
        if days:
            project.update(days=days)

        return project


class SeriesFillingSerializer(ProjectSerializer):
    class Meta:
        model = Project
        fields = ['client', 'user', 'money', 'money_per_day', 'money_calculating']
