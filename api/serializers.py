from django.contrib.auth.models import User
from rest_framework import serializers

from api.models import Project, Contact


class UserSerializer(serializers.Serializer):
    username = serializers.CharField()


class ContactSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    phone = serializers.CharField(allow_blank=True)

    def create(self, validated_data):
        return Contact.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.save()
        return instance


class ProjectShortSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    contact = ContactSerializer(allow_null=True)
    money = serializers.IntegerField(allow_null=True)


class ProjectSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    dates = serializers.ListField(child=serializers.DateField(), allow_empty=True)
    title = serializers.CharField(allow_blank=True)
    contact = ContactSerializer(allow_null=True)
    money = serializers.IntegerField(allow_null=True)
    info = serializers.CharField(allow_blank=True)
    creator = serializers.CharField(read_only=True)
    user = serializers.CharField()

    def create(self, validated_data):
        user = User.objects.get(username=validated_data['user'])
        contact, created = Contact.objects.get_or_create(name=validated_data['contact']['name'])
        serializer = ContactSerializer(contact, data=validated_data['contact'])
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            validated_data['contact'] = contact
            validated_data['user'] = User.objects.get(username=validated_data['user'])
        return Project.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.dates = validated_data.get('dates', instance.dates)
        instance.title = validated_data.get('title', instance.title)
        instance.money = validated_data.get('money', instance.money)
        instance.info = validated_data.get('info', instance.info)
        contact, created = Contact.objects.get_or_create(name=validated_data['contact']['name'])
        serializer = ContactSerializer(contact, data=validated_data['contact'])
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            validated_data['contact'] = contact
            instance.contact = validated_data.get('contact', instance.contact)

        instance.save()
        return instance


class UserProfileSerializer(serializers.Serializer):
    days_off = serializers.ListField(child=serializers.DateField(), allow_empty=True)

    def update(self, instance, validated_data):
        instance.days_off = validated_data.get('days_off', instance.days_off)
        instance.save()
        return instance

