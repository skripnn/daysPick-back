from django.contrib import admin
from django.contrib.auth.models import User

from api.models import Project, UserProfile, Day, Client


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    max_num = 1

class ClientsInline(admin.StackedInline):
    model = Client


class UserAdmin(admin.ModelAdmin):
    inlines = (UserProfileInline, ClientsInline)
    list_display = ('username', 'first_name', 'last_name', 'is_superuser', 'get_confirm')
    ordering = ('-is_superuser', 'username')

    def get_confirm(self, obj):
        return obj.profile.is_confirmed
    get_confirm.boolean = True
    get_confirm.short_description = 'E-mail status'
    get_confirm.admin_order_field = 'profile__is_confirmed'


class DayInline(admin.TabularInline):
    model = Day

class ProjectAdmin(admin.ModelAdmin):
    inlines = [DayInline]



admin.site.register(Project, ProjectAdmin)
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
admin.site.register(Day)
admin.site.register(Client)
