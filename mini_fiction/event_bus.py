import json
from abc import ABCMeta, abstractmethod
# noinspection PyUnresolvedReferences
import typing_extensions
from typing import Optional, Protocol, Dict, Any, runtime_checkable
from dataclasses import is_dataclass, asdict

from mini_fiction.settings import RedisConf


@runtime_checkable
class DataclassMessage(Protocol):
    __dataclass_fields__: Dict[Any, Any]


class EventBus(metaclass=ABCMeta):
    _config: RedisConf

    def __init__(self, *, config: Optional[RedisConf]):
        if config is None:
            raise ValueError("Failed to initialize event bus without configuration")
        self._config = config

    @abstractmethod
    def publish(self, topic: str, message: DataclassMessage) -> None:
        raise NotImplementedError


class NullEventBus(EventBus):
    # noinspection PyMissingConstructor,PyUnusedLocal
    def __init__(self, *, config: Optional[RedisConf] = None):
        # Intentionally allow to construct no-op instance
        pass

    def publish(self, topic: str, message: DataclassMessage) -> None:
        pass


class RedisEventBus(EventBus):
    def __init__(self, *, config: Optional[RedisConf]):
        super().__init__(config=config)
        import redis
        self.__redis = redis.Redis(**self._config)

    def publish(self, topic: str, message: DataclassMessage) -> None:
        if not is_dataclass(message):
            # Just in case
            raise ValueError(f"Only dataclasses allowed to passed by via event bus; got {message} ({type(message)})")
        # noinspection PyDataclass
        self.__redis.publish(topic, json.dumps(asdict(message)))
