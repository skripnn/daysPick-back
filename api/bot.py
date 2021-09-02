from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot, types
import re

from timespick.keys import TELEGRAM_TOKEN, admin_ids


bot = TeleBot(TELEGRAM_TOKEN)


class TelegramBot(APIView):
    permission_classes = ()

    def post(self, request, token=None):
        json_str = request.body.decode('UTF-8')
        update = types.Update.de_json(json_str)
        bot.process_new_updates([update])

        return Response({'code': 200})

    @staticmethod
    def account(func):
        def decorator(message, *args, **kwargs):
            from api.models import Account
            account = Account.objects.filter(telegram_chat_id=message.chat.id).first()
            func(message, *args, account=account, **kwargs)
        return decorator

    @staticmethod
    def error(message, error_message='Ошибка'):
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, error_message, reply_markup=keyboard)


class Phone:
    @staticmethod
    def enter(message):
        if message.text:
            phone(message, username=message.text)
        else:
            bot.send_message(message.chat.id, 'Нажми "Меню", чтобы увидеть команды')

    @staticmethod
    def confirmation(message, account=None, sign_up=False):
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        send = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
        cancel = types.KeyboardButton(text="Отмена")
        keyboard.add(send)
        keyboard.add(cancel)
        telephone_message = bot.send_message(message.chat.id, 'Отправь номер для подтверждения', reply_markup=keyboard)
        bot.register_next_step_handler(telephone_message, Phone.confirmation_answer, account, sign_up)

    @staticmethod
    def confirmation_answer(message, account, sign_up=False):
        if message.contact:
            if not message.contact.phone_number:
                TelegramBot.error(message)
            phone_number = message.contact.phone_number
            chat_id = message.chat.id
            if not account:
                if not sign_up:
                    TelegramBot.error(message)
                else:
                    data = {
                        'first_name': message.contact.first_name,
                        'last_name': message.contact.last_name,
                        'phone_confirm': phone_number,
                        'telegram_chat_id': chat_id
                    }
                    from api.models import Account
                    account = Account.get(message.from_user.username)
                    if not account:
                        data['username'] = message.from_user.username
                    account = Account.create(**data)
                    if account:
                        button = types.InlineKeyboardButton('Перейти на сайт', 'https://dayspick.ru/')
                        keyboard = types.InlineKeyboardMarkup().add(button)
                        bot.send_message(message.chat.id, f'Аккаунт успешно создан', reply_markup=keyboard)
                    else:
                        TelegramBot.error(message)
            else:
                keyboard = types.ReplyKeyboardRemove()
                if account.phone != phone_number and account.phone_confirm != phone_number:
                    keyboard = types.ReplyKeyboardRemove()
                    bot.send_message(message.chat.id, f'Ошибка', reply_markup=keyboard)
                    button = types.InlineKeyboardButton('Перейти на сайт', 'https://dayspick.ru/')
                    keyboard = types.InlineKeyboardMarkup().add(button)
                    bot.send_message(message.chat.id, f'Сначала измени телефон в настройках аккаунта на сайте',
                                     reply_markup=keyboard)
                    return
                if account.phone == phone_number:
                    account = account.update(phone_confirm=phone_number, phone=None, telegram_chat_id=chat_id)
                    from api.models import Account
                    if not isinstance(account, Account):
                        TelegramBot.error(message, 'Ошибка 122')
                    bot.send_message(message.chat.id, f'Номер подтвержден', reply_markup=keyboard)
                elif account.phone_confirm == phone_number:
                    bot.send_message(message.chat.id, f'Номер уже подтвержден', reply_markup=keyboard)
                button = types.InlineKeyboardButton('Перейти на сайт', 'https://dayspick.ru/')
                keyboard = types.InlineKeyboardMarkup().add(button)
                bot.send_message(message.chat.id, f'Можешь перейти на сайт', reply_markup=keyboard)
        elif message.text == 'Отмена':
            keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, f'Ну, в другой раз', reply_markup=keyboard)
        else:
            keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, f'Не понимаю тебя', reply_markup=keyboard)
            keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            send = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
            cancel = types.KeyboardButton(text="Отмена")
            keyboard.add(send)
            keyboard.add(cancel)
            next_message = bot.send_message(message.chat.id, f'Выбери одну из команд дополнительной клавиаутры',
                                            reply_markup=keyboard)
            bot.register_next_step_handler(next_message, Phone.confirmation_answer, account)


class Password:
    @staticmethod
    def enter(message, account, message_id):
        if message.text:
            new_password = message.text
            bot.delete_message(message.chat.id, message.message_id)
            bot.delete_message(message.chat.id, message_id)
            keyboard = types.ReplyKeyboardRemove()
            next_message = bot.send_message(message.chat.id, f'Введи новый пароль еще раз', reply_markup=keyboard)
            bot.register_next_step_handler(next_message, Password.confirmation, account, new_password, next_message.id)
        else:
            bot.send_message(message.chat.id, 'Нажми "Меню", чтобы увидеть команды')

    @staticmethod
    def confirmation(message, account, new_password, message_id):
        confirm_password = message.text
        bot.delete_message(message.chat.id, message.message_id)
        bot.delete_message(message.chat.id, message_id)
        if confirm_password == new_password:
            account.update(password=new_password)
            bot.send_message(message.chat.id, 'Пароль успешно изменён')
        else:
            TelegramBot.error(message, 'Пароли не совпадают')



@bot.message_handler(commands=['start'])
@TelegramBot.account
def start(message, account=None):
    if message.text != '/start':
        username = message.text[7:]
        phone(message, username)
        return
    if account:
        name = account.profile.first_name or account.username
    else:
        name = 'Незнакомец'
    keyboard = types.ReplyKeyboardRemove()
    hello_message = f'''
Привет, {name}.
Я - Бот сервиса DaysPick.
Нажми "Меню", чтобы увидеть команды.
    '''
    bot.send_message(message.chat.id, hello_message, reply_markup=keyboard)


@bot.message_handler(commands=['phone'])
@TelegramBot.account
def phone(message, username=None, account=None):
    if account:
        if not username or username == account.username:
            Phone.confirmation(message, account)
        else:
            keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, 'Невозможно подтвердить номер для второго аккаунта', reply_markup=keyboard)
    elif username and username != '/phone':
        account = validation_username(username)
        if account:
            Phone.confirmation(message, account)
        else:
            bot.send_message(message.chat.id, 'Пользователь не найден')
    else:
        keyboard = types.ReplyKeyboardRemove()
        start_message = bot.send_message(message.chat.id, 'Введи имя пользователя:', reply_markup=keyboard)
        bot.register_next_step_handler(start_message, Phone.enter)


@bot.message_handler(commands=['password'])
@TelegramBot.account
def password(message, account=None):
    if not account:
        return TelegramBot.error(message, 'Изменение пароля недоступно без подтвержденного номера телефона')
    keyboard = types.ReplyKeyboardRemove()
    next_message = bot.send_message(message.chat.id, 'Введи новый пароль:', reply_markup=keyboard)
    bot.register_next_step_handler(next_message, Password.enter, account, next_message.id)


@bot.message_handler(commands=['signup'])
@TelegramBot.account
def signup(message, account=None):
    if account:
        return TelegramBot.error(message, f'Ты уже зарегистрирован как {account.username}')
    Phone.confirmation(message, sign_up=True)


def validation_username(text):
    from api.models import Account
    if isinstance(text, Account):
        return text
    result = re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', text)
    if result:
        username = result.group(0).lower()
        account = Account.get(username)
        return account
    return None


# bot.set_webhook(url="https://47bb-176-193-135-241.ngrok.io/bot/" + TELEGRAM_TOKEN)
bot.set_webhook(url="https://dayspick.ru/bot/" + TELEGRAM_TOKEN)


class BotNotification:
    @classmethod
    def send_to_admins(cls, message):
        try:
            for i in admin_ids:
                bot.send_message(i, message)
        except:
            print("Can't connect to Bot")

    @classmethod
    def send(cls, profile, message, project):
        if profile and profile.account and profile.account.telegram_chat_id:
            try:
                button = types.InlineKeyboardButton('Посмотреть', f'https://dayspick.ru/project/{project.id}')
                keyboard = types.InlineKeyboardMarkup().add(button)
                bot.send_message(profile.account.telegram_chat_id, message, parse_mode='MarkdownV2', reply_markup=keyboard)
            except:
                print(f"Can't connect to Bot for send the message to {profile.full_name}:")
                print(message)

    @classmethod
    def create_project(cls, project):
        message = 'Получен запрос на проект'
        cls.send(project.user, message, project)

    @classmethod
    def accept_project(cls, project):
        message = f'Проект {project.title} был подтвержден пользователем {project.user.full_name}'
        cls.send(project.creator, message, project)

    @classmethod
    def decline_project(cls, project):
        message = f'Пользователь {project.user.full_name} отказался от проекта {project.title}'
        cls.send(project.creator, message, project)

    @classmethod
    def update_project(cls, project):
        message = f'Проект {project.title} был изменен'
        cls.send(project.user, message, project)

    @classmethod
    def cancel_project(cls, project):
        message = f'Проект {project.title} был отменён'
        cls.send(project.user, message, project)
