from abc import ABC, abstractmethod
from ..core.config import Settings


class BaseConverter(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    async def convert(self, *args, **kwargs) -> str:
        pass
