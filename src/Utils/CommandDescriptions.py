class CommandDescriptions(object):
    descriptions = {
        '/help': 'Show all available commands and a short description',
        '/start': 'Start chatting with me :)',
        '/website': 'Show the website-link of the team',
        '/stats': 'Choose to show the stats for trainings, games or timekeeping-events',
        '/edit': 'Choose to edit your attendance for trainings, games or timekeeping-events',
        '/games': 'Choose game to show or edit',
        '/trainings': 'Choose training to show or edit',
        '/timekeepings': 'Choose timekeeping-event to show or edit',
        '/game document_id': 'Indicate which game to edit / show',
        'overview': 'Go back to overview (choose game, training or timekeeping-event)',
        'continue later': 'Go back to main menu'
    }

    @classmethod
    def get_descriptions(cls, commands: list) -> str:
        commands.sort()
        message = 'Here are my available commands:\n'
        for command in commands:
            message += f'{command}: {cls.descriptions[command]}\n'
        return message
