import re
from abc import ABCMeta, abstractmethod
from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Sum, Count
from django.db.models.functions import Round
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, Client, Day, UserProfile, Tag, ProfileTag, ProjectResponse, Account
from api.serializers import ClientSerializer, TagSerializer, AccountSerializer, \
    ClientItemSerializer, ProfileItemSerializer, ProfileItemShortSerializer, \
    SeriesFillingSerializer, ProjectListItemSerializer, ProfileSerializer

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

    def get_paginator(self, queryset, data, **kwargs):
        page = int(data.get('page', 0))
        items = queryset.search(**data)
        paginator = Paginator(items, 15)
        pages = paginator.num_pages
        result = paginator.page(page + 1).object_list
        return {
            'list': self.serializer(result, many=True, **kwargs).data,
            'pages': pages
        }


class LoginView(APIView):
    permission_classes = ()

    @staticmethod
    def response(account):
        return Response({
            'token': account.token(),
            'account': AccountSerializer(account).data
        })

    def post(self, request):
        username = request.data.pop("username", None)
        password = request.data.pop("password")
        if not username:
            data = dict([(key + '_confirm', value) for key, value in request.data.items()])
            account = Account.objects.filter(**data).first()
            if account:
                username = account.username
        user = authenticate(username=username, password=password)
        if user:
            return self.response(user.account)
        return Response({"error": "Неверное имя пользователя или пароль"})


class LoginFacebookView(LoginView):
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
        return self.response(account)


class LoginTelegramView(LoginView):
    permission_classes = ()

    def post(self, request):
        account = Account.objects.filter(telegram_chat_id=request.data['id']).first()
        if not account:
            data = {
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name'),
                'telegram_chat_id': int(request.data.get('id'))
            }
            account = Account.create(**data)
        return self.response(account)


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


class RecoveryView(APIView):
    permission_classes = ()

    def get(self, request):
        account = Account.get(request.GET.get('user'))
        code = request.GET.get('code')
        token = account.token()[6:]
        if not account or not code or code != token:
            return Response({'error': 'Неверная ссылка'})
        return Response({
            'account': AccountSerializer(account).data,
            'token': account.token(new=True),
            'message': 'Доступ восстановлен. Рекомендуем установить новый пароль'
        })

    def post(self, request):
        key = request.data.get('type')
        value = request.data.get('value')
        chosen = request.data.get('chosen')
        if key not in ['username', 'email', 'phone'] or not value:
            return Response({'error': 'Неверные данные'})
        if key != 'username':
            field = key + '_confirm'
        else:
            field = 'user__' + key
        data = dict([(field, value)])
        account = Account.objects.filter(**data).first()
        if not account:
            return Response({'error': 'Пользователь не найден'})
        if key == 'phone' or chosen == 'phone':
            return Response({'message': 'telegram'})
        elif key == 'email' or chosen == 'email':
            account.send_recovery_email()
            return Response({'message': 'Код восстановления направлен на email'})
            pass
        else:
            if account.phone_confirm and account.email_confirm:
                return Response({'choice': True, 'message': 'Выбери способ восстановления досутпа:'})
            if account.phone_confirm:
                return Response({'message': 'telegram'})
            if account.email_confirm:
                account.send_recovery_email()
                return Response({'message': 'Код восстановления направлен на email'})
        return Response({'error': 'Непредвиденая ошибка'})


class ConfirmView(APIView):
    permission_classes = ()

    def get(self, request):
        account = Account.get(request.GET.get('user'))
        if account and account.confirm_email(request.GET.get('code')):
            return Response({
                'account': AccountSerializer(account).data,
                'token': account.token(),
                'message': 'Email подтверждён'
            })
        return Response({'error': 'Неверная ссылка'})


class ProfileView(APIView):
    permission_classes = ()

    def get(self, request, username=None):
        profile = UserProfile.get(username)
        asker = UserProfile.get(request)
        if profile:
            return Response(profile.page(asker, start=request.GET.get('start'), end=request.GET.get('end')))
        return Response({'error': f'Пользователь {username} не найден'})


class ProjectView(APIView):
    def get(self, request, pk=None):
        asker = UserProfile.get(request)
        if pk:
            project = Project.objects.filter(pk=pk).first()
            if project:
                page = project.page(asker)
                if page:
                    return Response(page)
        result = {
            'project': {
                'id': None,
                'title': None,
                'days': {},
                'money': None,
                'money_calculating': False,
                'money_per_day': None,
                'client': None,
                'user': None,
                'creator': ProfileItemShortSerializer(asker).data,
                'canceled': None,
                'is_paid': False,
                'is_wait': True,
                'info': None,
                'parent': None,
                'confirmed': False,
                'is_series': False
            },
            'calendar': {
                'days': {},
                'daysOff': []
            }
        }
        user = UserProfile.get(request.GET.get('user'))
        series = Project.get(request.GET.get('series'))
        copy = Project.get(request.GET.get('copy'))

        if series:
            user = series.user
            series_fields = SeriesFillingSerializer(series).data
            result['project'].update(series_fields)
            result['project'].update({
                'is_series': False,
                'parent': ProjectListItemSerializer(series).data
            })

        if user:
            result['project'].update({
                'user': ProfileItemShortSerializer(user).data,
                'is_wait': user != asker,
                'confirmed': user == asker
            })
            result['calendar'] = user.get_calendar(asker)

        if copy:
            page = copy.page(asker)
            if page:
                page['project']['id'] = None
                return Response(page)

        return Response(result)

    def post(self, request, pk=None):
        asker = UserProfile.get(request)
        if not pk:
            project = asker.create_project(request.data)
        else:
            project = asker.update_project(pk, request.data)
        if isinstance(project, Project):
            return Response(ProjectListItemSerializer(project).data)
        return Response(project)

    def delete(self, request, pk):
        asker = UserProfile.get(request)
        result = asker.delete_project(pk)
        return Response(result)


class ClientsView(ListView):
    serializer = ClientItemSerializer

    def search(self, request, data):
        profile = UserProfile.get(request)
        return Response(self.get_paginator(profile.clients, data))


class ClientsCompaniesView(APIView):
    def get(self, request):
        profile = UserProfile.get(request)
        companies = profile.clients.exclude(company='').order_by('company').values_list('company', flat=True).distinct()
        return Response(companies)


class ClientView(APIView):
    def get(self, request, pk):
        client = Client.objects.get(id=pk)
        return Response(ClientSerializer(client).data)

    def post(self, request, pk=None):
        profile = UserProfile.get(request)
        client = None
        if pk is not None:
            client = Client.objects.get(id=pk)
        serializer = ClientItemSerializer(client, data=request.data)
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
    serializer = ProfileItemSerializer

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
            user = asker
        projects = user.projects(asker)

        return Response(self.get_paginator(projects, data, asker=asker))


class OffersView(ListView):
    serializer = ProjectListItemSerializer

    def search(self, request, data):
        user = UserProfile.get(request)
        projects = user.offers()
        return Response(self.get_paginator(projects, data, asker=user))


class ProfileEditView(APIView):
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
        if request.data.get('password'):
            return Response({'token': account.token()})
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


class StatisticsView(APIView):
    def post(self, request, projects=None):
        dates = None
        if request.data:
            projects = projects.search(**request.data)
            dates = request.data.get('days')
        days = Day.objects.filter(project__in=projects)
        if dates:
            dates = [datetime.strptime(date, '%Y-%m-%d') for date in dates]
            days = days.filter(date__in=dates)
        # else:
        #     days = Day.objects.filter(project__user=profile, project__creator__isnull=False)

        result = days.aggregate(
            sum=Round(Sum('project__money_per_day')),
            days=Count('date', distinct=True),
            projects=Count('project', distinct=True))

        return Response(result)


class OffersStatisticsView(StatisticsView):
    def post(self, request, projects=None):
        profile = UserProfile.get(request)
        projects = profile.offers()
        return super().post(request, projects)


class ProjectsStatisticsView(StatisticsView):
    def post(self, request, projects=None):
        profile = UserProfile.get(request)
        projects = profile.projects()
        return super().post(request, projects)


class ProjectResponseView(APIView):
    def post(self, request, pk):
        profile = UserProfile.get(request)
        ProjectResponse.objects.get_or_create(project_id=pk, user=profile, **request.data)
        return Response(status=200)
