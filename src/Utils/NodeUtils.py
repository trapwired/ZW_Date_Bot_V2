from typing import Callable

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
        node.add_transition(command=event_string, action=event_function, allowed_roles=role_set,
                            needs_description=False, document_id=event.doc_id, event_type=event_type)
