from django.contrib import admin

from api.models import Project, Contact, UserProfile

admin.site.register(Project)
admin.site.register(Contact)
admin.site.register(UserProfile)
