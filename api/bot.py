from rest_framework.response import Response
from rest_framework.views import APIView
from telebot import TeleBot, types
import re

from api.models import UserProfile
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
    if isinstance(text, UserProfile):
        return text
    if text.startswith('/start '):
        text = text[7:]
    result = re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', text)
    if result:
        username = result.group(0).lower()
        username = UserProfile.get(username)
        return username
    return None


def telephone(message, username=None):
    if not username:
        if message.text == '/start':
            start(message)
            return
        username = message.text
    username = validation_username(username)
    if not username:
        start_message = bot.send_message(message.chat.id, 'Невозможное имя пользователя. Введи имя пользователя:')
        bot.register_next_step_handler(start_message, telephone)
        return
    keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    send = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)
    cancel = types.KeyboardButton(text="Отмена")
    keyboard.add(send)
    keyboard.add(cancel)
    telephone_message = bot.send_message(message.chat.id, 'Отправь номер для подтверждения', reply_markup=keyboard)
    bot.register_next_step_handler(telephone_message, answer, username)


def answer(message, profile):
    if message.contact:
        if not message.contact.phone_number:
            error(message)
        phone = message.contact.phone_number
        chat_id = message.chat.id
        if not profile:
            error(message)
        else:
            keyboard = types.ReplyKeyboardRemove()
            if profile.phone != phone and profile.phone_confirm != phone:
                return error(message)
            if profile.phone == phone:
                profile = profile.update(phone_confirm=phone, phone=None, telegram_chat_id=chat_id)
                if not isinstance(profile, UserProfile):
                    error(message)
                bot.send_message(message.chat.id, f'Номер подтвержден для пользователя {profile}', reply_markup=keyboard)
            elif profile.phone_confirm == phone:
                bot.send_message(message.chat.id, f'Номер уже подтвержден', reply_markup=keyboard)
            button = types.InlineKeyboardButton('Профиль', get_link('profile', profile))
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
        bot.register_next_step_handler(next_message, answer, profile)


def admins_notification(message):
    for i in admin_ids:
        bot.send_message(i, message)


def error(message):
    keyboard = types.ReplyKeyboardRemove()
    error_message = bot.send_message(message.chat.id, 'Ошибка. Введи имя пользователя:', reply_markup=keyboard)
    bot.register_next_step_handler(error_message, telephone)


def get_link(to, profile):
    return f'https://dayspick.ru/tgauth?user={profile.username}&code={profile.tg_code()}&to={to}'

# bot.set_webhook(url="https://ede629051ed7.ngrok.io/bot/" + TELEGRAM_TOKEN)
# bot.set_webhook(url="https://dayspick.ru/bot/" + TELEGRAM_TOKEN)


class BotNotification:
    @classmethod
    def send(cls, profile, message, project):
        button = types.InlineKeyboardButton('Посмотреть', get_link(f'project/{project.id}', profile))
        keyboard = types.InlineKeyboardMarkup().add(button)
        bot.send_message(profile.telegram_chat_id, message, parse_mode='MarkdownV2', reply_markup=keyboard)

    @classmethod
    def create_project(cls, project):
        if not project.user.telegram_chat_id:
            return
        message = 'Получен запрос на проект'
        cls.send(project.user, message, project)

    @classmethod
    def accept_project(cls, project):
        if not project.creator.telegram_chat_id:
            return
        message = f'Проект {project.title} был подтвержден пользователем {project.user.full_name}'
        cls.send(project.creator, message, project)

    @classmethod
    def decline_project(cls, project):
        if not project.creator.telegram_chat_id:
            return
        message = f'Пользователь {project.user.full_name} отказался от проекта {project.title}'
        cls.send(project.creator, message, project)

    @classmethod
    def update_project(cls, project):
        if not project.creator.telegram_chat_id:
            return
        message = f'Проект {project.title} был изменен'
        cls.send(project.user, message, project)

    @classmethod
    def cancel_project(cls, project):
        if not project.user.telegram_chat_id:
            return
        message = f'Проект {project.title} был отменён'
        cls.send(project.user, message, project)