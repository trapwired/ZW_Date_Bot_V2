from localization.Translator import t
from localization.CommandLabels import display_label


class CommandDescriptions(object):
    descriptions = {
        '/help': 'Show all available commands and a short description',
        '/start': 'Start chatting with me :)',
        '/privacy': 'Show the privacy policy of the bot',
        'events': 'Browse upcoming games, trainings and timekeeping-events - see who is coming and set your attendance',
        'admin': 'Open the admin menu: add events, statistics, roles and the website link',
        'website': 'Show the website-link of the team',
        '/cancel': 'Cancel the current input and go back to the main menu',
        '/language': 'Change the language I talk to you in',
    }

    @classmethod
    def get_descriptions(cls, commands: list) -> str:
        commands.sort()
        message = t('Here are my available commands:') + '\n'
        for command in commands:
            message += f'{display_label(command)}: {t(cls.descriptions[command])}\n'
        return message
