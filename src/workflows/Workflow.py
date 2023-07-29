from abc import ABC, abstractmethod


class Workflow(ABC):

    @abstractmethod
    def valid_commands(self):
        pass

    @abstractmethod
    def valid_states(self):
        pass

    @abstractmethod
    def handle(self):
        pass