import datetime
import logging

import telegram
from telegram import BotCommand
from telegram.ext import ApplicationBuilder, ContextTypes

from Utils.ApiConfig import ApiConfig

from framework import Heartbeat
from framework.CommandDescriptions import CommandDescriptions
from framework.NodeHandler import NodeHandler
from localization.Languages import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from localization.Translator import translate
from data.DataAccess import DataAccess

from features.attendance.IcsService import IcsService
from framework.Services.TelegramService import TelegramService
from framework.Services.UserStateService import UserStateService
from framework.Services.SchedulingService import SchedulingService
from framework.Services.TriggerService import TriggerService
from features.stats.StatisticsService import StatisticsService
from features.eventmgmt.EventService import EventService
from features.attendance.AttendanceService import AttendanceService
from features.roles.RoleService import RoleService
from framework.Services.TeamService import TeamService
from features.website.WebsiteService import WebsiteService


def initialize_logging():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )


def initialize_services(bot: telegram.Bot, api_config: ApiConfig):
    _data_access = DataAccess(api_config)
    _user_state_service = UserStateService(_data_access)
    _team_service = TeamService(_data_access)
    _telegram_service = TelegramService(bot, api_config, _user_state_service, _team_service)
    _ics_service = IcsService(_data_access, _team_service)
    _statistics_service = StatisticsService(_data_access)
    _scheduling_service = SchedulingService(_data_access, _telegram_service, _statistics_service, api_config)
    _trigger_service = TriggerService(_data_access, _telegram_service)
    _event_service = EventService(_data_access)
    _attendance_service = AttendanceService(_data_access)
    _role_service = RoleService(_data_access)
    _website_service = WebsiteService(_data_access)
    return _telegram_service, _user_state_service, _ics_service, _data_access, _scheduling_service, \
        _trigger_service, _event_service, _attendance_service, _role_service, _website_service, \
        _statistics_service, _team_service


async def send_hi(context: ContextTypes.DEFAULT_TYPE):
    await telegram_service.send_maintainer_hi('Bot was restarted')


MENU_COMMANDS = ['start', 'help', 'privacy', 'language']


async def register_bot_commands(context: ContextTypes.DEFAULT_TYPE):
    # Telegram's global command menu (the '/' button), one list per supported client
    # language. Everything else is reachable via the reply keyboard and inline menus.
    # 'gsw' is not a valid Telegram language_code (two-letter codes only), so Züridütsch
    # clients see the default menu; the /language picker itself is unaffected.
    def commands_for(language: str):
        return [BotCommand(name, translate(CommandDescriptions.descriptions['/' + name], language))
                for name in MENU_COMMANDS]

    await context.bot.set_my_commands(commands_for(DEFAULT_LANGUAGE))
    for language in SUPPORTED_LANGUAGES:
        if language != DEFAULT_LANGUAGE and len(language) == 2:
            await context.bot.set_my_commands(commands_for(language), language_code=language)


def run_job_queue():
    job_queue = application.job_queue
    job_queue.run_once(send_hi, 1)
    job_queue.run_once(register_bot_commands, 1)
    Heartbeat.register(job_queue)

    # Individual event reminders
    job_queue.run_daily(  # Game Reminders, each day at 11:59 local time
        scheduling_service.send_individual_game_reminders,
        datetime.time(9, 59, 0))

    job_queue.run_daily(  # Training Reminders, each day at 17:59 local time
        scheduling_service.send_individual_training_reminders,
        datetime.time(15, 59, 0))

    job_queue.run_daily(  # TKE Reminders, each day at 14:59 local time
        scheduling_service.send_individual_tke_reminders,
        datetime.time(12, 59, 0))

    # Summary to trainers / organisators
    job_queue.run_daily(  # Game summaries, each day at 7:59 local time
        scheduling_service.send_game_summary,
        datetime.time(5, 59, 0))

    job_queue.run_daily(  # Training summaries, each day at 18:59 local time
        scheduling_service.send_training_summary,
        datetime.time(16, 59, 0))

    job_queue.run_daily(  # Timekeeping summaries, each day at 18:59 local time
        scheduling_service.send_timekeeping_summary,
        datetime.time(16, 59, 0))

    # Game Reminder, on day of game
    job_queue.run_daily(  # same day at 7:00
        scheduling_service.send_same_day_game_reminder,
        datetime.time(6, 0, 0)
    )
    # Training Reminder, on day before training
    job_queue.run_daily(  # previous day at 20:30
        scheduling_service.send_previous_day_training_reminder,
        datetime.time(7, 30, 0)
    )


if __name__ == "__main__":
    initialize_logging()

    api_config = ApiConfig()

    application = ApplicationBuilder().token(api_config.get_key('Telegram', 'api_token')).build()

    telegram_service, user_state_service, ics_service, data_access, scheduling_service, trigger_service, \
        event_service, attendance_service, role_service, website_service, statistics_service, team_service = \
        initialize_services(application.bot, api_config)

    node_handler = NodeHandler(application.bot, api_config, telegram_service, user_state_service,
                               ics_service, data_access, trigger_service, event_service, attendance_service,
                               role_service, website_service, statistics_service, team_service)
    application.add_handler(node_handler)

    run_job_queue()

    application.run_polling()
