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


@bot.message_handler(commands=['start'])
def start(message, username=None):
    if message.text != '/start':
        telephone(message)
        return
    keyboard = types.ReplyKeyboardRemove()
    start_message = bot.send_message(message.chat.id, 'Введи имя пользователя:', reply_markup=keyboard)
    bot.register_next_step_handler(start_message, telephone, username)


def validation_username(text):
    from api.models import Account
    if isinstance(text, Account):
        return text
    if text.startswith('/start '):
        text = text[7:]
    result = re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', text)
    if result:
        username = result.group(0).lower()
        account = Account.get(username)
        return account
    return None


def telephone(message, username=None):
    if not username:
        if message.text == '/start':
            start(message)
            return
        username = message.text
    account = validation_username(username)
    if not account:
        start_message = bot.send_message(message.chat.id, 'Невозможное имя пользователя. Введи имя пользователя:')
        bot.register_next_step_handler(start_message, telephone)
        return
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    send = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
    cancel = types.KeyboardButton(text="Отмена")
    keyboard.add(send)
    keyboard.add(cancel)
    telephone_message = bot.send_message(message.chat.id, 'Отправь номер для подтверждения', reply_markup=keyboard)
    bot.register_next_step_handler(telephone_message, answer, account)


def answer(message, account):
    if message.contact:
        if not message.contact.phone_number:
            error(message)
        phone = message.contact.phone_number
        chat_id = message.chat.id
        if not account:
            error(message)
        else:
            keyboard = types.ReplyKeyboardRemove()
            if account.phone != phone and account.phone_confirm != phone:
                return error(message)
            if account.phone == phone:
                account = account.update(phone_confirm=phone, phone=None, telegram_chat_id=chat_id)
                from api.models import Account
                if not isinstance(account, Account):
                    error(message)
                bot.send_message(message.chat.id, f'Номер подтвержден для пользователя {account.username}', reply_markup=keyboard)
            elif account.phone_confirm == phone:
                bot.send_message(message.chat.id, f'Номер уже подтвержден', reply_markup=keyboard)
            button = types.InlineKeyboardButton('Профиль', get_link('profile', account))
            keyboard = types.InlineKeyboardMarkup().add(button)
            bot.send_message(message.chat.id, f'Можешь перейти в профиль', reply_markup=keyboard)
    elif message.text == 'Отмена':
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, f'Команда /start - подтвердить номер', reply_markup=keyboard)
    else:
        keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, f'Не понимаю тебя', reply_markup=keyboard)
        keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        send = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
        cancel = types.KeyboardButton(text="Отмена")
        keyboard.add(send)
        keyboard.add(cancel)
        next_message = bot.send_message(message.chat.id, f'Выбери одну из команд дополнительной клавиаутры', reply_markup=keyboard)
        bot.register_next_step_handler(next_message, answer, account)


def error(message):
    keyboard = types.ReplyKeyboardRemove()
    error_message = bot.send_message(message.chat.id, 'Ошибка. Введи имя пользователя:', reply_markup=keyboard)
    bot.register_next_step_handler(error_message, telephone)


def get_link(to, account):
    return f'https://dayspick.ru/tgauth?user={account.username}&code={account.tg_code()}&to={to}'


# bot.set_webhook(url="https://091ea319baa5.ngrok.io/bot/" + TELEGRAM_TOKEN)
# bot.set_webhook(url="https://dayspick.ru/bot/" + TELEGRAM_TOKEN)


class BotNotification:
    @classmethod
    def send_to_admins(cls, message):
        try:
            for i in admin_ids:
                # from .tasks import bot_send_message
                # bot_send_message.apply_async(i, message)
                bot.send_message(i, message)
        except:
            print("Can't connect to Bot")

    @classmethod
    def send(cls, profile, message, project):
        if profile and profile.telegram_chat_id:
            try:
                button = types.InlineKeyboardButton('Посмотреть', get_link(f'project/{project.id}', profile))
                keyboard = types.InlineKeyboardMarkup().add(button)
                # from .tasks import bot_send_message
                # bot_send_message(profile.telegram_chat_id, message, parse_mode='MarkdownV2', reply_markup=keyboard)
                bot.send_message(profile.telegram_chat_id, message, parse_mode='MarkdownV2', reply_markup=keyboard)
            except:
                print("Can't connect to Bot")

    @classmethod
    def create_project(cls, project):
        message = 'Получен запрос на проект'
        cls.send(project.account, message, project)

    @classmethod
    def accept_project(cls, project):
        message = f'Проект {project.title} был подтвержден пользователем {project.account.full_name}'
        cls.send(project.creator, message, project)

    @classmethod
    def decline_project(cls, project):
        message = f'Пользователь {project.account.full_name} отказался от проекта {project.title}'
        cls.send(project.creator, message, project)

    @classmethod
    def update_project(cls, project):
        message = f'Проект {project.title} был изменен'
        cls.send(project.account, message, project)

    @classmethod
    def cancel_project(cls, project):
        message = f'Проект {project.title} был отменён'
        cls.send(project.account, message, project)
