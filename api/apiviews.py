import re
import uuid
from abc import ABCMeta, abstractmethod
from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from api.bot import BotNotification
from api.models import Project, Client, Day, UserProfile, Tag, ProfileTag
from api.serializers import ProjectSerializer, ProfileSerializer, \
    ClientShortSerializer, ProfileSelfSerializer, CalendarDaySerializer, ClientSerializer, TagSerializer, \
    ProjectsListItemSerializer, ProfileShortSerializer

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


class ListView(APIView, metaclass=ABCMeta):
    def get(self, request):
        return self.search(request, request.GET)

    def post(self, request):
        return self.search(request, request.data)

    @abstractmethod
    def search(self, request, data):
        pass


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username").lower()
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        profile = UserProfile.get(user)
        if profile:
            if profile.is_confirmed:
                return Response(ProfileSerializer(profile).page(asker=profile, token=True))
            return Response({'error': 'Аккаунт не подтверждён'})
        return Response({"error": "Неверное имя пользователя или пароль"})


class TgAuthView(APIView):
    permission_classes = ()

    def get(self, request):
        code = int(request.GET.get('code', 0))
        user = request.GET.get('user')
        to = request.GET.get('to')

        if not all((code, user, to)):
            return Response({'error': 'Неверная ссылка'})
        profile = UserProfile.get(user)
        if code != profile.tg_code():
            return Response({'error': 'Ошибка авторизации'})
        return Response(profile.page(profile, token=True, additional={'to': to}))


class LoginFacebookView(APIView):
    permission_classes = ()

    def post(self, request):
        profile = UserProfile.objects.filter(facebook_account__id=request.data['id']).first()
        if not profile and request.data.get('email'):
            profile = UserProfile.objects.filter(email_confirm=request.data['email']).first()
            if profile:
                profile.update(facebook_account=request.data)
        if not profile:
            data = {
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'email_confirm': request.data.get('email')
            }
            profile = UserProfile.create(**data).update(facebook_account=request.data)
        return Response(profile.page(asker=profile, token=True))


class LoginTelegramView(APIView):
    permission_classes = ()

    def post(self, request):
        profile = UserProfile.objects.filter(telegram_chat_id=request.data['id']).first()
        if not profile:
            data = {
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'telegram_chat_id': int(request.data.get('id'))
            }
            profile = UserProfile.create(**data).update(telegram_chat_id=data['telegram_chat_id'])
        return Response(profile.page(asker=profile, token=True))


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
        asker = UserProfile.get(request.user)
        if not profile:
            return Response(status=404)
        if request.GET.get('projects'):
            return Response(ProjectSerializer(profile.get_actual_projects(asker), many=True).data)
        if request.GET.get('offers'):
            return Response(ProjectSerializer(profile.get_actual_offers(), many=True).data)
        if request.GET.get('profile'):
            if request.GET['profile'] == 'short':
                return Response(ProfileShortSerializer(profile).data)
            elif asker == profile:
                return Response(ProfileSelfSerializer(profile).data)
            return Response(ProfileSerializer(profile).data)
        return Response(profile.page(asker))

    def delete(self, request, username=None):
        profile = UserProfile.get(request.user)
        if profile:
            profile.delete()
            return Response({'status': 'ok'})
        return Response({'error': 'Пользователь не найден'})


class RaiseProfileView(APIView):
    def get(self, request):
        profile = request.user.profile
        profile.update(raised=timezone.now())
        return Response(profile.page(profile))


class ProjectView(APIView):
    def get(self, request, pk):
        if pk is not None:
            project = Project.objects.filter(pk=pk).first()
            if project:
                if any((request.user.profile == project.creator,
                        request.user.profile == project.user)) and request.user.profile != project.canceled:
                    return Response(ProjectSerializer(project).data)
        return Response(status=404)

    def post(self, request, pk=None):
        data = request.data
        if not data.get('user'):
            data['user'] = request.user.username
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            if project.creator != project.user:
                if request.user.profile == project.creator:
                    data.pop('is_paid')
                    data['confirmed'] = False
                else:
                    data['confirmed'] = True
                    data['is_wait'] = False
        else:
            if data.get('creator') != data.get('user'):
                data['is_wait'] = True
                data['confirmed'] = False
        serializer = ProjectSerializer(instance=project, data=data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()
            return Response(serializer.data)
        print(serializer.errors)
        return Response(status=500)

    def delete(self, request, pk):
        project = Project.objects.get(pk=pk)
        if project.parent:
            project.parent.child_delete(project)
        if project.creator != project.user and not project.canceled:
            project.canceled = request.user.profile
            project.confirmed = True
            project.is_wait = True
            project.save()
            if project.canceled == project.creator:
                BotNotification.cancel_project(project)
            elif project.canceled == project.user:
                BotNotification.decline_project(project)
        else:
            project.delete()

        return Response({})


class ClientsView(ListView):
    def search(self, request, data):
        return list_paginator(request.user.profile.clients, data, ClientShortSerializer)


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
        pick = request.data.get('pick')
        days = request.data.get('days', [])
        dates = [datetime.strptime(day, date_format).date() for day in days]
        if pick:
            existing = [day.date for day in Day.objects.filter(project=dop, date__in=dates)]
            dates = list(set(dates) - set(existing))
            objects = [Day(project=dop, date=date) for date in dates]
            Day.objects.bulk_create(objects)
        else:
            Day.objects.filter(project=dop, date__in=dates).delete()
        return Response({})


class UsersView(ListView):
    permission_classes = ()

    def search(self, request, data):
        return list_paginator(UserProfile, data, ProfileSerializer)


class CalendarView(APIView):
    permission_classes = ()

    def get(self, request):
        asker = UserProfile.get(request.user)
        start, end = request.GET.get('start'), request.GET.get('end')
        if start:
            start = datetime.strptime(start, date_format).date()
        if end:
            end = datetime.strptime(end, date_format).date()
        result = {}
        if asker and request.GET.get('offers'):
            result[asker.username] = asker.get_calendar(start=start, end=end, offers=True)
            return Response(result)
        project_id = int(request.GET.get('project_id', 0))
        users = request.GET.getlist('users')
        if not users:
            users = request.GET.getlist('user')

        for user in users:
            user_profile = UserProfile.get(user)
            if user_profile:
                result[user] = user_profile.get_calendar(asker, start, end, project_id)

        return Response(result)


class TestView(ListView):
    def search(self, request, data):
        projects = request.user.profile.projects().without_children()
        return list_paginator(projects, {}, ProjectsListItemSerializer)


class ProjectsView(ListView):
    def search(self, request, data):
        user = UserProfile.get(data.get('user'))
        asker = UserProfile.get(request.user)
        if not user:
            if data.get('open'):
                projects = Project.objects.filter(user__isnull=True)
            else:
                projects = asker.projects()
        elif user == asker:
            projects = user.projects()
        else:
            projects = user.projects(asker).filter(creator=asker)

        return list_paginator(projects, data, ProjectSerializer)


class OffersView(ListView):
    def search(self, request, data):
        user = UserProfile.get(request.user)
        projects = user.offers()
        return list_paginator(projects, data, ProjectSerializer)


class UserProfileView(APIView):
    def post(self, request):
        profile = request.user.profile.update(**request.data)
        return Response(ProfileSelfSerializer(profile).data)


class ImgView(APIView):
    def post(self, request):
        profile = request.user.profile.update(**request.FILES)
        return Response(ProfileSelfSerializer(profile).data)


class TagsView(APIView):
    def get(self, request):
        tags = Tag.search(profile=request.user.profile, **request.GET)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request):
        tags = request.user.profile.tags.update(request.data)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def put(self, request):
        tag, created = Tag.objects.get_or_create(**request.data)
        count = request.user.profile.tags.count()
        request.user.profile.tags.add(
            ProfileTag.objects.create(tag=tag, rank=count)
        )
        serializer = TagSerializer(request.user.profile.tags.list(), many=True)
        return Response(serializer.data)
