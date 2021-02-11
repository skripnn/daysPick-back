from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Project, Client, Day, UserProfile
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
                             'user': ProfileSerializer(user).data['username']})
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

    def get(self, request, user=None):
        user_db = User.objects.filter(username=user).first()
        if not user_db:
            return Response(status=404)
        if user_db != request.user:
            data = ProfileSerializer(user_db.profile).data
        else:
            data = ProfileSelfSerializer(user_db.profile).data
        return Response(data)


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
        clients = request.user.profile.clients.all()
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
        users = User.objects.filter(is_superuser=False, profile__is_confirmed=True)
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
        user = UserProfile.objects.get(user__username=request.GET.get('user'))
        if user == request.user.profile:
            projects = Project.objects.filter(user=user).exclude(creator__isnull=True)
        else:
            projects = Project.objects.filter(user=user, creator=request.user.profile)
        return Response(ProjectSerializer(projects, many=True).data)
