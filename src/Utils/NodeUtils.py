import datetime
from functools import partial
from typing import Callable
import pytz

from Enums.Event import Event
from Enums.RoleSet import RoleSet

from Nodes.Node import Node

from Utils.CustomExceptions import NoEventFoundException
from Utils import PrintUtils


def add_event_transitions_to_node(event_type: Event, node: Node, event_function: Callable):
    try:
        events = []
        role_set = RoleSet.EVERYONE
        match event_type:
            case Event.GAME:
                events = node.data_access.get_ordered_games()
            case Event.TRAINING:
                events = node.data_access.get_ordered_trainings()
            case Event.TIMEKEEPING:
                events = node.data_access.get_ordered_timekeepings()
                role_set = RoleSet.PLAYERS
    except NoEventFoundException:
        return

    for event in events:
        event_string = PrintUtils.pretty_print(event)
        # TODO add other func? or make self.state fat / mark somehow??
        additional_data_func = partial(node.data_access.get_stats_event, event_id=event.doc_id, event_type=event_type)

        is_active_function = partial(is_in_future, timestamp=event.timestamp)
        node.add_event_transition(command=event_string, action=event_function, allowed_roles=role_set,
                                  needs_description=False, document_id=event.doc_id, event_type=event_type,
                                  additional_data_func=additional_data_func, is_active_function=is_active_function)


def is_in_future(timestamp: datetime, x=5):
    tz = pytz.timezone('Europe/Zurich')
    now = datetime.datetime.now(tz=tz)
    return timestamp > now
