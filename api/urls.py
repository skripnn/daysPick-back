"""timespick URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path

from api.apiviews import ProjectView, LoginView, SignupView, DaysOffView, ProfilesView, \
    ConfirmView, CalendarView, ProjectsView, ClientsView, ClientView, ProfileEditView, \
    ProfileTagsView, ImgView, LoginFacebookView, LoginTelegramView, OffersView, \
    ProjectsStatisticsView, ProjectResponseView, AccountView, RecoveryView, ProfileView, OffersStatisticsView, \
    ClientsCompaniesView, FavoritesView, TagsView

urlpatterns = [
    path('login/facebook/', LoginFacebookView.as_view()),
    path('login/telegram/', LoginTelegramView.as_view()),
    path('login/', LoginView.as_view()),

    path('signup/', SignupView.as_view()),

    path('confirm/', ConfirmView.as_view()),
    path('recovery/', RecoveryView.as_view()),

    path('users/', ProfilesView.as_view()),

    path('tags/', TagsView.as_view()),
    path('profile/tags/', ProfileTagsView.as_view()),
    path('profile/img/', ImgView.as_view()),
    path('profile/', ProfileEditView.as_view()),

    path('account/', AccountView.as_view()),

    path('daysoff/', DaysOffView.as_view()),

    path('calendar/offers/', CalendarView.as_view()),
    path('calendar/', CalendarView.as_view()),

    path('offers/statistics/', OffersStatisticsView.as_view()),
    path('offers/', OffersView.as_view()),
    path('projects/statistics/', ProjectsStatisticsView.as_view()),
    path('projects/', ProjectsView.as_view()),
    path('project/<int:pk>/response/', ProjectResponseView.as_view()),
    path('project/<int:pk>/', ProjectView.as_view()),
    path('project/', ProjectView.as_view()),

    path('clients/companies/', ClientsCompaniesView.as_view()),
    path('clients/', ClientsView.as_view()),
    path('client/<int:pk>/', ClientView.as_view()),
    path('client/', ClientView.as_view()),

    path('favorites/', FavoritesView.as_view()),

    path('@<str:username>/', ProfileView.as_view()),
    path('', ProfilesView.as_view())
]
