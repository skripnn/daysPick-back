from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, Contact
from api.serializers import ProjectSerializer, ContactSerializer, UserProfileSerializer, \
    ProjectShortSerializer


class FunctionsMixin:
    def get_all_projects(self, username, data=None):
        if data is None:
            data = {}
        user = User.objects.get(is_active=True)
        all_projects = Project.objects.filter(user__username=username)
        projects = all_projects.filter(creator=user)
        for project in projects:
            project.dates.sort()
        for project in all_projects.exclude(creator=user):
            user.profile.days_off.extend(project.dates)
        user.profile.days_off = list(set(user.profile.days_off))
        user.profile.days_off.sort()

        data.update({
            'projects': ProjectShortSerializer(projects, many=True).data,
            'daysOff': UserProfileSerializer(user.profile).data['days_off']
        })
        return data


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            return Response({"token": user.auth_token.key})
        return Response({"error": "Wrong Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class ProjectsView(APIView, FunctionsMixin):
    def get(self, request, user):
        return Response(self.get_all_projects(user))


class ProjectView(APIView, FunctionsMixin):
    def get(self, request, user, pk=None):
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            project.dates.sort()
        data = {'project': ProjectSerializer(project).data}
        if request.GET.get('full') is not None:
            data = self.get_all_projects(user, data)
        return Response(data)

    def post(self, request, user, pk=None):
        data = request.data
        data['dates'].sort()
        data['user'] = user
        data['contact']['user'] = user
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
        serializer = ProjectSerializer(instance=project, data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(self.get_all_projects(user))
        return Response(status=500)

    def delete(self, request, user, pk):
        Project.objects.get(pk=pk).delete()
        return Response(self.get_all_projects(user))


class DaysOffView(APIView, FunctionsMixin):
    def get(self, request, user):
        user = User.objects.get(is_active=True)
        user.profile.days_off.sort()
        return Response(UserProfileSerializer(user.profile).data['days_off'])

    def post(self, request, user):
        user = User.objects.get(is_active=True)
        serializer = UserProfileSerializer(instance=user.profile, data={'days_off': request.data})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(self.get_all_projects(user))
        return Response(status=500)


class ClientsView(APIView):
    def get(self, request, user):
        clients = Contact.objects.filter(user__username=user).order_by('name')
        return Response(ContactSerializer(clients, many=True).data)
