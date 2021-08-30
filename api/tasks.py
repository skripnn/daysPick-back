from timespick.celery import app


@app.task(name='Удаление неподтвержденных пользователей')
def check_user_confirmation(username):
    from api.models import Account
    account = Account.get(username)
    if account:
        if not account.telegram_chat_id and not account.is_confirmed:
            account.delete()
            print(f'Account {username} was deleted because it was not confirmed')


@app.task(name='Уведомления администраторам')
def bot_admin_notification(message):
    from api.bot import BotNotification
    BotNotification.send_to_admins(message)


@app.task(name='Сообщение пользователю')
def bot_send_message(*args, **kwargs):
    from api.bot import bot
    bot.send_message(*args, **kwargs)
