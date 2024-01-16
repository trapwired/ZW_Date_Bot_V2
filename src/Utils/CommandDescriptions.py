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
        '/admin': 'Admin stuff like adding / updating events',
        '/add': 'Add a new event (triggers a message to all)',
        '/update': 'Update / Delete a upcoming event',
        'overview': 'Go back to overview (choose game, training or timekeeping-event)',
        'continue later': 'Go back to main menu',
        '/cancel': 'Go Back to main admin menu',
        '/reminder_statistics': 'Show reminder statistics for all players',
        '/game_statistics': 'Show game-attendance statistics for all players',
        '/training_statistics': 'Show training-attendance statistics for all players',
        '/timekeeping_statistics': 'Show timekeeping-attendance statistics for all players',
        '/statistics': 'Go to statistics menu'
    }

    @classmethod
    def get_descriptions(cls, commands: list) -> str:
        commands.sort()
        message = 'Here are my available commands:\n'
        for command in commands:
            message += f'{command}: {cls.descriptions[command]}\n'
        return message

