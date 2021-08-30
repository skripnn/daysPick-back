import re
from abc import ABCMeta, abstractmethod
from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from django.db.models.functions import Round
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from api.bot import BotNotification
from api.models import Project, Client, Day, UserProfile, Tag, ProfileTag, ProjectResponse, Account
from api.serializers import ProjectSerializer, ProfileSerializer, \
    ClientShortSerializer, ClientSerializer, TagSerializer, \
    ProjectListItemSerializer, ProfileShortSerializer, AccountSerializer

date_format = '%Y-%m-%d'


class ListView(APIView, metaclass=ABCMeta):
    serializer = ...

    def get(self, request):
        return self.search(request, request.GET)

    def post(self, request):
        return self.search(request, request.data)

    @abstractmethod
    def search(self, request, data):
        pass

    def get_paginator(self, queryset, data):
        page = int(data.get('page', 0))
        items = queryset.search(**data)
        paginator = Paginator(items, 15)
        pages = paginator.num_pages
        result = paginator.page(page + 1).object_list
        return {
            'list': self.serializer(result, many=True).data,
            'pages': pages
        }


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username").lower()
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            account = user.account
            return Response({
                'token': account.token(),
                'account': AccountSerializer(account).data
            })
        return Response({"error": "Неверное имя пользователя или пароль"})


class TgAuthView(APIView):
    permission_classes = ()

    def get(self, request):
        code = int(request.GET.get('code', 0))
        user = request.GET.get('user')
        to = request.GET.get('to')

        if not all((code, user, to)):
            return Response({'error': 'Неверная ссылка'})
        account = Account.get(user)
        if code != account.tg_code():
            return Response({'error': 'Ошибка авторизации'})
        return Response(account.profile.page(account.profile, token=True, additional={'to': to}))


class LoginFacebookView(APIView):
    permission_classes = ()

    def post(self, request):
        account = Account.objects.filter(facebook_account__id=request.data['id']).first()
        if not account and request.data.get('email'):
            account = Account.objects.filter(email_confirm=request.data['email']).first()
            if account:
                account.update(facebook_account=request.data)
        if not account:
            data = {
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'email_confirm': request.data.get('email')
            }
            account = Account.create(**data).update(facebook_account=request.data)
        return Response(account.profile.page(asker=account.profile, token=True))


class LoginTelegramView(APIView):
    permission_classes = ()

    def post(self, request):
        account = Account.objects.filter(telegram_chat_id=request.data['id']).first()
        if not account:
            data = {
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'telegram_chat_id': int(request.data.get('id'))
            }
            account = Account.create(**data).update(telegram_chat_id=data['telegram_chat_id'])
        return Response(account.profile.page(asker=account.profile, token=True))


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
        Account.create(**request.data)
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
            if Account.objects.filter(email_confirm=email).count() != 0:
                error = 'Пользователь с таким e-mail уже зарегистрирован'
        if phone:
            if Account.objects.filter(phone_confirm=phone).count() != 0:
                error = 'Пользователь с таким телефоном уже зарегистрирован'
        return error


class ConfirmView(APIView):
    permission_classes = ()

    def get(self, request):
        profile = UserProfile.get(request.GET.get('user'))
        if profile and profile.account:
            return Response({'result': profile.account.confirm_email(request.GET.get('code'))})
        return Response({'result': None})


class UserView(APIView):
    permission_classes = ()

    def get(self, request, username=None):
        profile = UserProfile.get(username)
        asker = UserProfile.get(request)
        if not profile:
            return Response({'error': f'Пользователь {username} не найден'})
        if request.GET.get('projects'):
            return Response(ProjectListItemSerializer(profile.get_actual_projects(asker), many=True).data)
        if request.GET.get('offers'):
            return Response(ProjectListItemSerializer(profile.get_actual_offers(), many=True).data)
        if request.GET.get('profile'):
            if request.GET['profile'] == 'short':
                return Response(ProfileShortSerializer(profile).data)
            return Response(ProfileSerializer(profile).data)
        return Response(profile.page(asker))


class RaiseProfileView(APIView):
    def get(self, request):
        profile = UserProfile.get(request)
        if profile:
            profile = profile.update(raised=timezone.now())
            return Response(profile.page(profile))
        return Response({'error': 'Профиль не найден'})


class ProjectView(APIView):
    def get(self, request, pk):
        asker = UserProfile.get(request)
        if pk is not None:
            project = Project.objects.filter(pk=pk).first()
            if project:
                if not project.user:
                    return Response(ProjectSerializer(project).data)
                if any((asker == project.creator,
                        asker == project.user,)) and asker != project.canceled:
                    return Response(ProjectSerializer(project).data)
        return Response(status=404)

    def post(self, request, pk=None):
        asker = UserProfile.get(request)
        data = request.data
        project = None
        if pk is not None:
            project = Project.objects.get(pk=pk)
            if project.creator != project.user:
                if asker == project.creator:
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
        else:
            print(serializer.errors)
            try:
                project.update(**data)
                return Response(ProjectSerializer(project).data)
            except Exception as e:
                print(e)
        return Response(status=500)

    def delete(self, request, pk):
        asker = UserProfile.get(request)
        project = Project.objects.get(pk=pk)
        if project.parent:
            project.parent.child_delete(project)
        if project.creator != project.user and not project.canceled:
            project.canceled = asker
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
    serializer = ClientShortSerializer

    def search(self, request, data):
        profile = UserProfile.get(request)
        return Response(self.get_paginator(profile.clients, data))


class ClientView(APIView):
    def get(self, request, pk):
        client = Client.objects.get(id=pk)
        return Response(ClientSerializer(client).data)

    def post(self, request, pk=None):
        profile = UserProfile.get(request)
        client = None
        if pk is not None:
            client = Client.objects.get(id=pk)
        serializer = ClientShortSerializer(client, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=profile)
            return Response(serializer.data)
        return Response(status=500)

    def delete(self, request, pk):
        Client.objects.get(id=pk).delete()
        return Response({})


class DaysOffView(APIView):

    def post(self, request):
        profile = UserProfile.get(request)
        dop = profile.days_off_project
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


class ProfilesView(ListView):
    permission_classes = ()
    serializer = ProfileSerializer

    def search(self, request, data):
        return Response(self.get_paginator(UserProfile, data))


class CalendarView(APIView):
    permission_classes = ()

    def get(self, request):
        asker = UserProfile.get(request)
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


class ProjectsView(ListView):
    serializer = ProjectListItemSerializer

    def search(self, request, data):
        user = UserProfile.get(data.get('user'))
        asker = UserProfile.get(request)
        if not user:
            if data.get('open'):
                projects = Project.objects.filter(user__isnull=True)
            else:
                projects = asker.projects()
        elif user == asker:
            projects = user.projects()
        else:
            projects = user.projects(asker).filter(creator=asker)

        return Response(self.get_paginator(projects, data))


class OffersView(ListView):
    serializer = ProjectListItemSerializer

    def search(self, request, data):
        user = UserProfile.get(request)
        projects = user.offers()
        return Response(self.get_paginator(projects, data))


class UserProfileView(APIView):
    def post(self, request):
        profile = UserProfile.get(request)
        if profile:
            profile = profile.update(**request.data)
            return Response(ProfileSerializer(profile).data)
        return Response({'error': 'Профиль не найден'})


class AccountView(APIView):
    def get(self, request):
        account = request.user.account
        return Response(AccountSerializer(account).data)

    def post(self, request):
        account = request.user.account.update(**request.data)
        return Response(AccountSerializer(account).data)

    def delete(self, request):
        account = request.user.account
        if account:
            account.delete()
            return Response({'status': 'ok'})
        return Response({'error': 'Пользователь не найден'})


class ImgView(APIView):
    def post(self, request):
        profile = UserProfile.get(request)
        if profile:
            profile = profile.update(**request.FILES)
            return Response(ProfileSerializer(profile).data)
        return Response({'error': 'Профиль не найден'})


class TagsView(APIView):
    def get(self, request):
        profile = UserProfile.get(request)
        tags = Tag.search(profile=profile, **request.GET)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def post(self, request):
        profile = UserProfile.get(request)
        tags = profile.tags.update(request.data)
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)

    def put(self, request):
        profile = UserProfile.get(request)
        tag, created = Tag.objects.get_or_create(**request.data)
        count = profile.tags.count()
        profile.tags.add(
            ProfileTag.objects.create(tag=tag, rank=count)
        )
        serializer = TagSerializer(profile.tags.list(), many=True)
        return Response(serializer.data)


class ProjectsStatisticsView(APIView):
    def post(self, request):
        profile = UserProfile.get(request)

        if request.data:
            projects = profile.projects().search(**request.data)
            days = Day.objects.filter(project__in=projects)
            dates = request.data.get('days')
            if dates:
                dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]
                days = days.filter(date__in=dates)
        else:
            days = Day.objects.filter(project__user=profile, project__creator__isnull=False)

        result = days.aggregate(
            sum=Round(Sum('project__money_per_day')),
            days=Count('date', distinct=True),
            projects=Count('project', distinct=True))

        return Response(result)


class ProjectResponseView(APIView):
    def post(self, request, pk):
        profile = UserProfile.get(request)
        ProjectResponse.objects.get_or_create(project_id=pk, user=profile, **request.data)
        return Response(status=200)
