from django.contrib.auth.models import User
from rest_framework import serializers
from api.models import Project


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()


class ProjectShortSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = serializers.CharField()
    money = serializers.IntegerField(allow_null=True)


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    client = serializers.CharField()
    money = serializers.IntegerField(allow_null=True)
    info = serializers.CharField(allow_blank=True)
    creator = serializers.CharField(read_only=True)
    user = serializers.CharField()

    def create(self, validated_data):
        validated_data['user'] = User.objects.get(username=validated_data['user'])
        return Project.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.dates = validated_data.get('dates', instance.dates)
        instance.title = validated_data.get('title', instance.title)
        instance.money = validated_data.get('money', instance.money)
        instance.client = validated_data.get('client', instance.client)
        instance.info = validated_data.get('info', instance.info)

        instance.save()
        return instance


class UserProfileSerializer(serializers.Serializer):
    days_off = serializers.ListField(child=serializers.DateField(), allow_empty=True)

    def update(self, instance, validated_data):
        instance.days_off = validated_data.get('days_off', instance.days_off)
        instance.save()
        return instance

