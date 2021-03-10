import re
from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, Client, Day, UserProfile, Tag, ProfileTag
from api.serializers import ProjectSerializer, ProfileSerializer, \
    ClientShortSerializer, ProfileSelfSerializer, CalendarDaySerializer, ClientSerializer, TagSerializer

date_format = '%Y-%m-%d'


def list_paginator(_class, data, serializer):
    page = int(data.get('page', 0))
    items = _class.search(**data)
    paginator = Paginator(items, 15)
    pages = paginator.num_pages
    result = paginator.page(page + 1).object_list
    return Response({
        'list': serializer(result, many=True).data,
        'pages': pages
    })


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username").lower()
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            if not user.profile.is_confirmed:
                return Response({'error': 'Аккаунт не подтверждён'})
            token, created = Token.objects.get_or_create(user=user)
            projects = user.profile.get_actual_projects(user.profile)
            return Response({
                'token': token.key,
                'user': {
                    'user': ProfileSelfSerializer(user.profile).data,
                    'projects': ProjectSerializer(projects, many=True).data
                }
            })
        return Response({"error": "Неверное имя пользователя или пароль"})


class SignupView(APIView):
    permission_classes = ()

    def get(self, request):
        params = {key: (value[0] if isinstance(value, list) else value) for key, value in request.GET.items()}
        error = self.validate(**params)
        if error:
            return Response({'error': error})
        return Response({})

    def post(self, request):
        error = self.validate(**request.data)
        if request.data.get('password') != request.data.get('password2'):
            error = 'Пароли не совпадают'
        if error:
            return Response({'error': error})
        UserProfile.create(**request.data)
        return Response({})

    def validate(self, **kwargs):
        username = kwargs.get("username")
        email = kwargs.get("email")
        phone = kwargs.get("phone")
        error = None
        if username:
            if re.match('^[^a-zA-Z]', username):
                error = 'Имя пользователя может начаинаться только с латинской буквы'
            elif len(username) < 4:
                error = 'Имя пользователя не может быть короче 4х симоволов'
            elif re.match('[^a-z0-9_]', username):
                error = 'Имя пользователя может содержать только латинские буквы, цифры и нижнее подчеркивание'
            elif User.objects.filter(username=username).count() != 0:
                error = 'Имя пользователя занято'
        if email:
            if UserProfile.objects.filter(email_confirm=email).count() != 0:
                error = 'Пользователь с таким e-mail уже зарегистрирован'
        if phone:
            if UserProfile.objects.filter(phone_confirm=phone).count() != 0:
                error = 'Пользователь с таким телефоном уже зарегистрирован'
        return error


class ConfirmView(APIView):
    permission_classes = ()

    def get(self, request):
        profile = UserProfile.get(request.GET.get('user'))
        if profile:
            return Response({'result': profile.confirm_email(request.GET.get('code'))})
        return Response({'result': None})


class UserView(APIView):
    permission_classes = ()

    def get(self, request, username=None):
        profile = UserProfile.get(username)
        request_profile = UserProfile.get(request.user)
        if not profile:
            return Response(status=404)
        if profile == request_profile:
            user = ProfileSelfSerializer(profile).data
        else:
            user = ProfileSerializer(profile).data
        projects = profile.get_actual_projects(request_profile)
        if projects:
            projects = ProjectSerializer(projects, many=True).data
        return Response({
            'user': user,
            'projects': projects or []
        })


class ProjectView(APIView):
    def get(self, request, pk):
        if pk is None:
            return Response({})
        project = Project.objects.get(pk=pk)
        return Response(ProjectSerializer(project).data)

    def post(self, request, pk=None):
        data = request.data
        data['user'] = request.GET.get('user', request.user.username)
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            data['creator'] = project.creator.username
        else:
            data['creator'] = request.user.username
        serializer = ProjectSerializer(instance=project, data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)
        return Response(status=500)

    def delete(self, request, pk):
        Project.objects.get(pk=pk).delete()
        return Response({})


class ClientsView(APIView):
    def get(self, request):
        return list_paginator(request.user.profile.clients, request.GET, ClientShortSerializer)

    def post(self, request):
        return list_paginator(request.user.profile.clients, request.data, ClientShortSerializer)


class ClientView(APIView):
    def get(self, request, pk):
        client = Client.objects.get(id=pk)
        return Response(ClientSerializer(client).data)

    def post(self, request, pk=None):
        client = None
        if pk is not None:
            client = Client.objects.get(id=pk)
        serializer = ClientShortSerializer(client, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=request.user.profile)
            return Response(serializer.data)
        return Response(status=500)

    def delete(self, request, pk):
        Client.objects.get(id=pk).delete()
        return Response({})


class DaysOffView(APIView):

    def post(self, request):
        dop = request.user.profile.days_off_project
        date = datetime.strptime(request.data, date_format).date()
        day, created = Day.objects.get_or_create(project=dop, date=date)
        if not created:
            day.delete()
        return Response({})


class UsersView(APIView):
    permission_classes = ()

    def get(self, request):
        return list_paginator(UserProfile, request.GET, ProfileSerializer)

    def post(self, request):
        return list_paginator(UserProfile, request.data, ProfileSerializer)


class CalendarView(APIView):
    permission_classes = ()

    def get(self, request):
        start = datetime.strptime(request.GET.get('start'), date_format).date()
        end = datetime.strptime(request.GET.get('end'), date_format).date()
        project_id = int(request.GET.get('project_id', 0))
        user = request.GET.get('user')

        all_days = Day.objects.filter(date__range=[start, end], project__user__user__username=user).exclude(project_id=project_id)
        if request.user.is_anonymous:
            days_off = all_days.exclude(project__is_wait=True).dates('date', 'day')
            days = {}
        else:
            days_off = all_days.exclude(project__creator=request.user.profile).dates('date', 'day')
            days = all_days.filter(project__creator=request.user.profile)
            days = CalendarDaySerializer(days, many=True).dict()

        return Response({
            'days': days,
            'daysOff': days_off
        })


class ProjectsView(APIView):
    def get(self, request):
        return self.search(request, request.GET)

    def post(self, request):
        return self.search(request, request.data)

    def search(self, request, data):
        user = UserProfile.get(data.get('user'))
        asker = UserProfile.get(request.user)
        if not user:
            user = asker
        if user == asker:
            projects = user.projects
        else:
            projects = user.projects.filter(creator=asker)

        return list_paginator(projects, data, ProjectSerializer)


class UserProfileView(APIView):
    def post(self, request):
        profile = request.user.profile.update(**request.data)
        return Response(ProfileSelfSerializer(profile).data)


class TagsView(APIView):
    def get(self, request):
        if request.GET.get('filter') == 'options':
            tags = Tag.objects.filter(custom=False, parent=None)
        else:
            tags = request.user.profile.tags.list()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request):
        tags = request.user.profile.tags.update(request.data)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def put(self, request):
        tag, created = Tag.objects.get_or_create(**request.data)
        if created:
            tag.custom = True
            tag.save()
        request.user.profile.tags.add(
            ProfileTag.objects.create(tag=tag, rank=request.user.profile.tags.count())
        )
        return self.get(request)
