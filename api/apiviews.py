from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.functions import Length
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, Client, Day, UserProfile, Position
from api.serializers import ProjectSerializer, ProfileSerializer, \
    ClientShortSerializer, ProfileSelfSerializer, CalendarDaySerializer, ClientSerializer

date_format = '%Y-%m-%d'


class LoginView(APIView):
    permission_classes = ()

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            if not user.profile.is_confirmed:
                return Response({'error': 'Please confirm your e-mail'})
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key,
                             'user': user.username})
        return Response({"error": "Wrong login or password"}, status=status.HTTP_400_BAD_REQUEST)


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

        User.objects.create_user(username=username, password=password, email=email)

        letter = {
            'theme': 'DaysPick e-mail confirmation',
            'body': f'Confirm your account {username} on link: http://dayspick.ru/confirm/?user={username}&code={abs(hash(username))}',
            'from': 'DaysPick <registration@dayspick.ru>',
            'to': [email]
        }
        print(f'http://dayspick.ru/confirm/?user={username}&code={abs(hash(username))}')
        try:
            send_mail(letter['theme'],
                      letter['body'],
                      letter['from'],
                      letter['to'])
        except Exception as e:
            print(f'SEND MAIL ERROR: {e}')
        return Response({})


class ConfirmView(APIView):
    permission_classes = ()

    def get(self, request):
        if abs(hash(request.GET.get('user'))) == int(request.GET.get('code')):
            user = User.objects.get(username=request.GET.get('user'))
            user.profile.is_confirmed = True
            user.save()
            return Response({'result': True})
        return Response({'result': False})


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
        clients = request.user.profile.clients.search(
            filter=request.GET.get('filter'),
            name=request.GET.get('name'),
            company=request.GET.get('company')
        )
        return Response(ClientShortSerializer(clients, many=True).data)


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
        users = UserProfile.objects.filter(is_confirmed=True, user__is_superuser=False)
        return Response(ProfileSerializer(users, many=True).data)


class CalendarView(APIView):
    permission_classes = ()

    def get(self, request):
        start = datetime.strptime(request.GET.get('start'), date_format).date()
        end = datetime.strptime(request.GET.get('end'), date_format).date()
        project_id = int(request.GET.get('project_id', 0))
        user = request.GET.get('user')

        all_days = Day.objects.filter(date__range=[start, end], project__user__user__username=user).exclude(project_id=project_id)
        if request.user.is_anonymous:
            days_off = all_days.dates('date', 'day')
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
        user = UserProfile.get(request.GET.get('user'))
        asker = UserProfile.get(request.user)
        if user == asker:
            projects = user.projects.search(request.GET.get('filter'))
        else:
            projects = user.projects.filter(creator=asker).search(request.GET.get('filter'))
        return Response(ProjectSerializer(projects, many=True).data)


class PositionView(APIView):
    def get(self, request, position):
        position = Position.objects.filter(title__istartswith=position).order_by(Length('title').asc()).first()
        result = ''
        if position:
            result = position.title
        return Response(result)

    def put(self, request, position):
        position, created = Position.objects.get_or_create(title=position)
        request.user.profile.positions.add(position)
        return Response(ProfileSelfSerializer(request.user.profile).data['positions'])

    def delete(self, request, position):
        position = Position.objects.filter(title=position).first()
        if position:
            request.user.profile.positions.remove(position)
        if not position.profiles.count():
            position.delete()
        return Response(ProfileSelfSerializer(request.user.profile).data['positions'])


class UserProfileView(APIView):
    def post(self, request):
        data = request.user.profile.update(request.data)
        return Response(data)
