import configparser
import traceback

import telegram
from multipledispatch import dispatch
from telegram import ReplyKeyboardMarkup, Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from Enums.MessageType import MessageType
from Enums.Event import Event

from Utils import PrintUtils
from Utils.ApiConfig import ApiConfig

from databaseEntities.TelegramUser import TelegramUser


def get_text(message_type: MessageType, extra_text: str = '', first_name: str = ''):
    match message_type:
        case MessageType.ERROR:
            return 'Something went wrong - please try again, the maintainer has been notified :)'
        case MessageType.HELP:
            return 'Help is on its way (' + extra_text + ')'
        case MessageType.WRONG_START_COMMAND:
            return 'Please start chatting with me by sending the command /start'
        case MessageType.WELCOME:
            return 'Hi ' + first_name + ', welcome to the Züri west manager'
        case MessageType.CONTINUE_LATER:
            return 'Cheerio ' + first_name + '!'
        case MessageType.WEBSITE:
            return 'Here you go :)'

        case MessageType.REJECTED:
            return 'I am sorry, you are not allowed to use this bot. If you think this is wrong, contact the person ' \
                   'you got the bot recommended from... :)'

        case MessageType.STATS_OVERVIEW:
            return 'Do you want to show stats for a game, training or timekeeping-event?'
        case MessageType.STATS_TO_GAMES:
            return 'Click on the game you want to see the stats for'
        case MessageType.STATS_TO_TRAININGS:
            return 'Click on the training you want to see the stats for'
        case MessageType.STATS_TO_TIMEKEEPINGS:
            return 'Click on the timekeeping-event you want to see the stats for'

        case MessageType.EDIT_OVERVIEW:
            return 'Do you want to edit your attendance for a game, training or timekeeping-event?'
        case MessageType.EDIT_TO_GAMES:
            return 'Click on the game you want to change your attendance-status'
        case MessageType.EDIT_TO_TRAININGS:
            return 'Click on the training you want to change your attendance-status'
        case MessageType.EDIT_TO_TIMEKEEPINGS:
            return 'Click on the timekeeping-event you want to change your attendance-status'

        case MessageType.ADMIN:
            return 'Welcome to the admin-center - here you can add, update and delete upcoming events...'
        case MessageType.ADMIN_ADD:
            return 'What kind of event do you want to add?'
        case MessageType.ADMIN_UPDATE:
            return 'Which kind of event do you want to update (or delete)?'
        case MessageType.ADMIN_UPDATE_TO_GAME:
            return 'Click on the game you want to update or delete'
        case MessageType.ADMIN_UPDATE_TO_TRAINING:
            return 'Click on the training you want to update or delete'
        case MessageType.ADMIN_UPDATE_TO_TIMEKEEPING:
            return 'Click on the timekeeping-event you want to update or delete'

        case MessageType.TKE_ALREADY_FULL:
            return 'For the chosen timekeeping event already enough people have registered'

        case MessageType.ENROLLMENT_REMINDER:
            return 'Hey ' + first_name + ', please quickly take your time to update your attendance for the following upcoming event(s):'

        case MessageType.EVENT_TIMESTAMP_CHANGED:
            return 'Hey ' + first_name + ', the following event was moved by more than 2 hours. I reset your previous answer - please quickly fill out your attendance for the moved event - thanks'

        case _:
            return message_type.name + ' ' + extra_text


def generate_keyboard(all_commands: [str]) -> [[str]]:
    first_cmds = ['overview', 'continue later']
    firsts = []
    events = []
    commands = []
    for cmd in all_commands:
        if cmd[0].isdigit():
            events.append(cmd)
        elif cmd in first_cmds:
            firsts.append(cmd)
        elif cmd != '/help':
            commands.append(cmd)

    result = [firsts]
    result.extend([e] for e in events)

    max_line_length = 15
    current_line_length = 0
    current_line = []
    for c in commands:
        if current_line_length + len(c) < max_line_length:
            current_line.append(c)
            current_line_length += len(c)
        else:
            result.append(current_line)
            current_line_length = len(c)
            current_line = [c]
    if len(current_line) > 0:
        result.append(current_line)
    result.append(['/help'])
    return result


class TelegramService(object):
    def __init__(self, bot: telegram.Bot, api_config: ApiConfig):
        self.bot = bot
        self.maintainer_chat_id = api_config.get_key('Chat_Ids', 'MAINTAINER')
        self.website = api_config.get_key('Additional_Data', 'WEBSITE')
        self.trainers_games = api_config.get_int_list('Chat_Ids', 'TRAINERS_GAMES')
        self.trainers_training = api_config.get_int_list('Chat_Ids', 'TRAINERS_TRAINING')

    async def send_message(self, update: Update | TelegramUser, all_buttons: [str], message_type: MessageType = None,
                           message: str = None, message_extra_text: str = '', reply_markup=None):
        chat_id = update.effective_chat.id if type(update) is Update else update.telegramId
        first_name = update.effective_user.first_name if type(update) is Update else update.firstname
        if message is None:
            message = get_text(message_type, first_name=first_name, extra_text=message_extra_text)
        if reply_markup is None:
            reply_markup = self.get_reply_keyboard(message_type, all_buttons)
        message_to_send = PrintUtils.prepare_message(message)
        return await self.bot.send_message(chat_id=chat_id, text=message_to_send, reply_markup=reply_markup,
                                           parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    async def send_message_with_normal_keyboard(self, update: Update | TelegramUser, message: str):
        chat_id = update.effective_chat.id if type(update) is Update else update.telegramId
        message_to_send = PrintUtils.prepare_message(message)
        await self.bot.send_message(chat_id=chat_id, text=message_to_send, reply_markup=ReplyKeyboardRemove(),
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    async def send_info_message_to_trainers(self, message: str, event_type: Event):
        message_to_send = PrintUtils.prepare_message(message)
        chat_ids = self.get_chat_ids(event_type)
        for chat_id in chat_ids:
            await self.bot.send_message(chat_id=chat_id, text=message_to_send, reply_markup=None,
                                        parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    @dispatch(str)
    async def send_maintainer_message(self, message: str):
        message = 'INFO: ' + message
        message_to_send = PrintUtils.prepare_message(message)
        await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    @dispatch(str, Exception)
    async def send_maintainer_message(self, description: str, error: Exception):
        error_message = repr(error) + '\n' + traceback.format_exc()
        text = 'ERROR: ' + description + '\n\n' + error_message
        message_to_send = PrintUtils.prepare_message(text)
        await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    @dispatch(str, Update, Exception)
    async def send_maintainer_message(self, description: str, update: Update, error: Exception):
        error_message = repr(error) + '\n' + traceback.format_exc()
        text = 'ERROR: ' + description + '\n\n' + str(update) + '\n\n' + error_message
        message_to_send = PrintUtils.prepare_message(text)
        await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    async def send_maintainer_hi(self, hi: str):
        message_to_send = PrintUtils.prepare_message(hi)
        await self.bot.send_message(chat_id=int(self.maintainer_chat_id), text=message_to_send,
                                    parse_mode=telegram.constants.ParseMode.MARKDOWN_V2)

    def get_reply_keyboard(self, message_type: MessageType, all_commands: [str]):
        match message_type:
            case MessageType.WRONG_START_COMMAND:
                keyboard = [['/start']]
                return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            case MessageType.WEBSITE:
                return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="handball.ch/Züri West 1",
                                                                                   url=self.website)]])
            case MessageType.REJECTED:
                return None

        if all_commands is None or len(all_commands) == 0:
            return None
        keyboard = generate_keyboard(all_commands)
        return ReplyKeyboardMarkup(keyboard, one_time_keyboard=False)

    def get_chat_ids(self, event_type):
        match event_type:
            case Event.GAME:
                return self.trainers_games
            case Event.TRAINING:
                return self.trainers_training
            case Event.TIMEKEEPING:
                return self.trainers_games
        return []

    async def edit_inline_message_text(self, message: str, message_id: int, chat_id: int):
        await self.bot.edit_message_text(text=message, message_id=message_id, chat_id=chat_id)
