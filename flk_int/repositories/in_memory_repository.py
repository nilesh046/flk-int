from abc import ABC, abstractmethod


class Repository(ABC):
    @abstractmethod
    def save(self, entity):
        pass

    @abstractmethod
    def find_by_id(self, entity_id: str):
        pass

    @abstractmethod
    def find_all(self):
        pass


class InMemoryRepository(Repository):
    def __init__(self):
        self._store = {}

    def save(self, entity):
        raise NotImplementedError

    def find_by_id(self, entity_id: str):
        raise NotImplementedError

    def find_all(self):
        raise NotImplementedError
