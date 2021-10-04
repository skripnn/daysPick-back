from django.contrib import admin
from django.contrib.auth.models import User

from api.models import Project, UserProfile, Day, Client, Tag, ProfileTag, FacebookAccount, ProjectShowing, Account


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    max_num = 1


class ClientsInline(admin.StackedInline):
    model = Client


class TagInline(admin.TabularInline):
    model = Tag


class TagsInline(admin.TabularInline):
    model = ProfileTag


class UserAdmin(admin.ModelAdmin):
    def profile_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse('admin:api_userprofile_change', args=[obj.account.profile.id])
        return format_html("<a href='{}'>{}</a>", url, str(obj.account.profile))

    profile_link.admin_order_field = 'profile'
    profile_link.short_description = 'profile'

    # inlines = (UserProfileInline,)
    list_display = ('username', 'profile_link', 'is_superuser')
    ordering = ('-is_superuser', 'username')


class DayInline(admin.TabularInline):
    model = Day


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_title', 'creator', 'user', 'client', 'is_paid')
    inlines = [DayInline]

    def get_title(self, obj):
        return str(obj)

    get_title.short_description = 'title'


@admin.register(Day)
class DayAdmin(admin.ModelAdmin):
    list_display = ('date', 'project', 'info')


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'user')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('title', 'default')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('account', 'first_name', 'last_name')
    inlines = (TagsInline,)


@admin.register(ProjectShowing)
class ProjectShowingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'user', 'time', 'response')


@admin.register(ProfileTag)
class ProfileTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'tag', 'user')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(FacebookAccount)
admin.site.register(Account)
