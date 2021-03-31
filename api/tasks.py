from timespick.celery import app


@app.task(name='Удаление неподтвержденных пользователей')
def check_user_confirmation(username):
    from api.models import UserProfile
    profile = UserProfile.get(username)
    if profile:
        if not profile.is_confirmed:
            profile.delete()
            print(f'Profile {username} was deleted because it was not confirmed')
