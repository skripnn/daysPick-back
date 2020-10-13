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

from api.apiviews import ProjectView, ProjectsView, LoginView, DaysOffView, ClientsView

urlpatterns = [
    path('<user>/login/', LoginView.as_view()),
    path('<user>/project/<int:pk>/', ProjectView.as_view()),
    path('<user>/project/', ProjectView.as_view()),
    path('<user>/daysoff/', DaysOffView.as_view()),
    path('<user>/clients/', ClientsView.as_view()),
    path('<user>/', ProjectsView.as_view())
]
