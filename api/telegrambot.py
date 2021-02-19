import re

from telegram import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler
from django_telegrambot.apps import DjangoTelegramBot
from telebot import types

import logging

from .models import Telegram, UserProfile
from .utils import phone_format

logger = logging.getLogger(__name__)

TELEPHONE, ANSWER, START = range(3)


def start(update, context):
    keyboard = ReplyKeyboardRemove()
    if update.message.text != '/start':
        return telephone(update, context)
    update.message.reply_text(text='Введи имя пользователя:', reply_markup=keyboard)
    return TELEPHONE


def error(update, context):
    keyboard = ReplyKeyboardRemove()
    update.message.reply_text(text='Ошибка. Введи имя пользователя:', reply_markup=keyboard)
    return TELEPHONE


def validation_username(text):
    if text.startswith('/start '):
        text = text[7:]
    result = re.match(r'^[a-zA-Z][a-zA-Z]*$', text)
    if result:
        username = result.group(0).lower()
        username = UserProfile.get(username)
        return username
    return None


def telephone(update, context):
    profile = validation_username(update.message.text)
    if not profile:
        update.message.reply_text('Неверное имя пользователя. Введи имя пользователя:')
        return TELEPHONE

    tg, created = Telegram.objects.get_or_create(chat_id=update.effective_chat.id)
    tg.profile = profile
    tg.save()

    send = KeyboardButton(text="Отправить номер телефона", request_contact=True)
    back = KeyboardButton(text="Отмена")
    keyboard = ReplyKeyboardMarkup([[send], [back]], one_time_keyboard=True, resize_keyboard=True)

    update.message.reply_text('Отправь номер для подтверждения', reply_markup=keyboard)
    return ANSWER


def answer(update, context):
    if update.message.contact:
        phone = phone_format(update.message.contact.phone_number)
        chat_id = update.effective_chat.id

        tg = Telegram.objects.filter(chat_id=update.effective_chat.id, profile__isnull=False).first()
        if not tg:
            return error(update, context)
        else:
            button = types.InlineKeyboardButton('Профиль', f'https://dayspick.ru/profile/')
            clear = ReplyKeyboardRemove()
            keyboard = types.InlineKeyboardMarkup().add(button)
            if tg.profile.phone == phone:
                tg.profile.update(phone_confirm=phone, phone=None, telegram_chat_id=chat_id)
                update.message.reply_text('Номер подтвержден. Ссылка на профиль', reply_markup=clear)
                update.message.reply_text('Можешь перейти в профиль', reply_markup=keyboard.to_json())
            elif tg.profile.phone_confirm == phone:
                update.message.reply_text('Номер уже подтвержден', reply_markup=clear)
                update.message.reply_text('Можешь перейти в профиль', reply_markup=keyboard.to_json())
            else:
                return error(update, context)
    else:
        return start(update, context)


def main():
    dp = DjangoTelegramBot.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={

            TELEPHONE: [MessageHandler(Filters.text, telephone)],

            ANSWER: [MessageHandler(Filters.text | Filters.contact, answer)],

            START: [CommandHandler('start', start)],
        },

        fallbacks=[CommandHandler('start', start)]
    )
    dp.add_handler(conv_handler)
