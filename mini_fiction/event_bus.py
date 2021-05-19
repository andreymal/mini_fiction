import json
from abc import ABCMeta, abstractmethod
from typing import Any, Optional

from mini_fiction.settings import RedisConf


class EventBus(metaclass=ABCMeta):
    _config: RedisConf

    def __init__(self, *, config: Optional[RedisConf]):
        if config is None:
            raise ValueError("Failed to initialize event bus without configuration")
        self._config = config

    @abstractmethod
    def publish(self, topic: str, message: Any) -> None:
        raise NotImplementedError


class NullEventBus(EventBus):
    # noinspection PyMissingConstructor,PyUnusedLocal
    def __init__(self, *, config: Optional[RedisConf] = None):
        # Intentionally allow to construct no-op instance
        pass

    def publish(self, topic: str, message: Any) -> None:
        pass


class RedisEventBus(EventBus):
    def __init__(self, *, config: Optional[RedisConf]):
        super().__init__(config=config)
        import redis
        self.__redis = redis.Redis(**self._config)

    def publish(self, topic: str, message: Any) -> None:
        self.__redis.publish(topic, json.dumps(message))
