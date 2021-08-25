from timespick.celery import app


@app.task(name='Удаление неподтвержденных пользователей')
def check_user_confirmation(username):
    from api.models import UserProfile
    profile = UserProfile.get(username)
    if profile:
        if not profile.telegram_chat_id and not profile.is_confirmed:
            profile.delete()
            print(f'Profile {username} was deleted because it was not confirmed')


@app.task(name='Уведомления администраторам')
def bot_admin_notification(message):
    from api.bot import admins_notification
    admins_notification(message)


@app.task(name='Сообщение пользователю')
def bot_send_message(*args, **kwargs):
    from api.bot import bot
    bot.send_message(*args, **kwargs)
