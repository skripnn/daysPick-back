from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, UserProfile
from api.serializers import ProjectSerializer, UserProfileSerializer, ProjectShortSerializer, UserSerializer


class FunctionsMixin:
    def get_all_projects(self, username, auth_user, data=None):
        user = User.objects.get(username=username)
        if data is None:
            data = {}
        all_projects = Project.objects.filter(user=user)
        if auth_user.is_anonymous:
            for project in all_projects.all():
                user.profile.days_off.extend(project.dates)
            user.profile.days_off = list(set(user.profile.days_off))
            projects = []
        elif user != auth_user:
            projects = all_projects.filter(creator=auth_user)
            for project in projects:
                project.dates.sort()
            for project in all_projects.exclude(creator=auth_user):
                user.profile.days_off.extend(project.dates)
            user.profile.days_off = list(set(user.profile.days_off))
        else:
            projects = all_projects
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
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key,
                             'user': UserSerializer(user).data['username']})
        return Response({"error": "Wrong Credentials"}, status=status.HTTP_400_BAD_REQUEST)


class SignupView(APIView):
    permission_classes = ()

    def get(self, request):
        username = request.GET.get("username")
        if len(User.objects.filter(username=username)) != 0:
            return Response({'error': 'Username already in use'})
        return Response({})

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        user = User.objects.create_user(username=username, password=password, email=email)
        UserProfile.objects.create(user=user)
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key,
                             'user': UserSerializer(user).data['username']})
        return Response({"error": "Something wrong"})


class ProjectsView(APIView, FunctionsMixin):
    permission_classes = ()

    def get(self, request, user=None):
        if user is None:
            user = request.user
        return Response(self.get_all_projects(user, request.user))


class ProjectView(APIView, FunctionsMixin):
    def get(self, request, pk=None):
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            project.dates.sort()
            user = project.user
        else:
            user = request.GET.get('user', request.user.username)
        data = {'project': ProjectSerializer(project).data}
        data = self.get_all_projects(user, request.user, data)
        return Response(data)

    def post(self, request, pk=None):
        data = request.data
        data['dates'].sort()
        data['user'] = request.GET.get('user', request.user.username)
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            data['creator'] = project.creator.username
        else:
            data['creator'] = request.user.username
            if data['user'] != data['creator']:
                data['status'] = 'new'
        serializer = ProjectSerializer(instance=project, data=data)
        print(serializer.is_valid())
        print(serializer.errors)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response({})
        return Response(status=500)

    def delete(self, request, pk):
        Project.objects.get(pk=pk).delete()
        return Response({})


class DaysOffView(APIView, FunctionsMixin):
    def get(self, request):
        user = request.user
        user.profile.days_off.sort()
        return Response(UserProfileSerializer(user.profile).data['days_off'])

    def post(self, request):
        user = request.user
        serializer = UserProfileSerializer(instance=user.profile, data={'days_off': request.data})

        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(self.get_all_projects(user, user))
        return Response(status=500)


class ClientsView(APIView):
    def get(self, request):
        return Response({})


class UsersView(APIView):
    def get(self, request):
        users = User.objects.filter(is_superuser=False)
        return Response(UserSerializer(users, many=True).data)
