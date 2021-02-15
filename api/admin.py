from django.contrib import admin
from django.contrib.auth.models import User

from api.models import Project, UserProfile, Day, Client, Position


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    max_num = 1


class ClientsInline(admin.StackedInline):
    model = Client


class UserAdmin(admin.ModelAdmin):
    def profile_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:api_userprofile_change', args=[obj.profile.id])
        return format_html("<a href='{}'>{}</a>", url, str(obj.profile))
    profile_link.admin_order_field = 'profile'
    profile_link.short_description = 'profile'

    inlines = (UserProfileInline,)
    list_display = ('username', 'profile_link', 'is_superuser')
    ordering = ('-is_superuser', 'username')


class DayInline(admin.TabularInline):
    model = Day


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'creator', 'title', 'client', 'is_paid')
    inlines = [DayInline]


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('date', 'project', 'info')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'user')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'first_name', 'last_name', 'is_confirmed')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Position)
