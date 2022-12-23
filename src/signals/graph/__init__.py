import abc
import collections
import enum
import functools
import typing

import attr
import more_itertools
import numpy as np


class Shape(typing.NamedTuple):
    """
    >>> s = Shape(frames=10, channels=2)
    >>> s
    Shape(frames=10, channels=2)
    >>> t = tuple(s)
    >>> t
    (10, 2)
    >>> s == t
    True
    >>> s <= t
    True
    >>> s >= t
    True
    >>> s == (1, 1)
    False
    >>> (1, 1) <= Shape(frames=s.frames, channels=1) <= s
    True
    >>> (1, 1) <= Shape(frames=1, channels=s.channels) <= s
    True
    >>> (0, 0) <= s
    False
    >>> Shape(frames=3, channels=2) <= s
    False
    >>> Shape(frames=10, channels=0) <= s
    False
    """
    frames: int
    channels: int

    def __le__(self, other: tuple[int, int]) -> bool:
        return (self[0] in (1, other[0])) and (self[1] in (1, other[1]))

    def __ge__(self, other: tuple[int, int]) -> bool:
        return (other[0] in (1, self[0])) and (other[1] in (1, self[1]))

    @classmethod
    def of_array(cls, array: np.ndarray) -> typing.Self:
        return cls(*array.shape)

    def grow(self, new_frames: int) -> typing.Self:
        return Shape(frames=self.frames + new_frames,
                     channels=self.channels)


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class BlockLoc:
    position: int
    shape: Shape

    @property
    def stop(self) -> int:
        return self.position + self.shape[0]


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Request:
    sink: 'Node'
    loc: BlockLoc

    def resize(self, new_frames: int) -> typing.Self:
        return Request(sink=self.sink,
                       loc=BlockLoc(position=self.loc.position,
                                    shape=Shape(frames=new_frames, channels=self.loc.shape.channels)))


class _Slot(property):
    pass


class _Control(property):
    pass


class NodeType(enum.Enum):
    GENERATOR = enum.auto()
    OPERATOR = enum.auto()
    PLAYBACK = enum.auto()
    TABLE = enum.auto()
    VALUE = enum.auto()


class RequestRate(enum.Enum):
    UNKNOWN = enum.auto()
    BLOCK = enum.auto()
    FRAME = enum.auto()
    UNUSED_FRAME = enum.auto()


SlotName = str


class Node(abc.ABC):

    def __init__(self):
        self._sources: dict[SlotName, Node] = {}
        self._sinks: set[Node] = set()
        self.enabled: bool = True
        self._last_reqest: typing.Optional[Request] = None

    @property
    @abc.abstractmethod
    def type(self) -> NodeType:
        raise NotImplementedError

    @property
    def rate(self) -> RequestRate:
        if self._last_reqest is None:
            return RequestRate.UNKNOWN
        else:
            frames = self._last_reqest.loc.shape.frames
            if frames <= 0:
                return RequestRate.UNKNOWN
            elif frames == 1:
                return RequestRate.BLOCK
            else:
                return RequestRate.FRAME

    @classmethod
    def slots(cls) -> list[SlotName]:
        return [
            k
            for k in dir(cls)
            if isinstance(getattr(cls, k), _Slot)
        ]

    @classmethod
    def controls(cls) -> list[str]:
        return [
            k
            for k in dir(cls)
            if isinstance(getattr(cls, k), _Control)
        ]

    @property
    def sources(self) -> typing.Iterable['Node']:
        return map(self._sources.__getitem__, self.slots())

    @property
    def sinks(self) -> typing.Iterable['Node']:
        return self._sinks

    def upstream(self) -> typing.Sequence['Node']:
        return self._upstream(set())

    def _upstream(self, visited: set['Node']) -> collections.deque['Node']:
        result = collections.deque()
        for source in self.sources:
            if source not in visited:
                result.extend(source._upstream(visited))
                visited.update(result)
        assert self not in visited, 'Cycle detected'
        result.append(self)
        return result

    def request(self, source: 'Node', loc: BlockLoc) -> np.ndarray:
        block = source.respond(self._make_request(loc))
        assert block.shape <= loc.shape, (block.shape, loc.shape)
        return block

    def forward_request(self,
                        source: 'Node',
                        request: Request,
                        new_shape: typing.Optional[Shape] = None
                        ) -> np.ndarray:
        loc = request.loc if new_shape is None else BlockLoc(position=request.loc.position,
                                                             shape=new_shape)
        return self.request(source, loc)

    def forward_sample_request_to_block_request(self,
                                                source: 'Node',
                                                request: Request
                                                ) -> np.ndarray:
        return self.forward_request(source,
                                    request,
                                    Shape(channels=request.loc.shape.channels,
                                          frames=1))

    @functools.lru_cache(maxsize=2)
    def _make_request(self, loc: BlockLoc):
        return Request(sink=self, loc=loc)

    def respond(self, request: Request) -> np.ndarray:
        self._last_reqest = request
        return self._get_result(request)

    def destroy(self) -> None:
        for slot in self.slots():
            delattr(self, slot)

    @abc.abstractmethod
    def _eval(self, request: Request) -> np.ndarray:
        raise NotImplementedError

    def _get_result(self, request: Request) -> np.ndarray:
        return self._eval(request) if self.enabled else 0

    @property
    @abc.abstractmethod
    def channels(self) -> int:
        raise NotImplementedError


def slot(name: SlotName) -> _Slot:
    def fget(self: Node) -> typing.Optional[Node]:
        return self._sources.get(name)

    def fdel(self: Node) -> None:
        old_source = self._sources.pop(name)
        old_source._sinks.remove(self)

    def fset(self: Node, source: Node) -> None:
        try:
            old_source = self._sources[name]
        except KeyError:
            pass
        else:
            old_source._sinks.remove(self)
        self._sources[name] = source
        source._sinks.add(self)

    return _Slot(fget=fget, fset=fset, fdel=fdel)


class PassThroughShape(Node, abc.ABC):

    @property
    def channels(self) -> int:
        input_shape = {source.channels for source in self.sources}
        if len(input_shape) > 1:
            input_shape.discard(1)
        return more_itertools.one(input_shape)


class NotCached(RuntimeError):
    pass


class BlockCachingNode(Node, abc.ABC):

    def __init__(self):
        super().__init__()
        self._block_cache = None
        self._block_cache_position = None
        self._block_cache_users = set()

    def _read_block_cache(self, request: Request) -> np.ndarray:
        if (
            self._block_cache is not None
            and self._block_cache_position == request.loc.position
            and self._block_cache.shape[0] >= request.loc.shape[0]
        ):
            return self._block_cache
        else:
            raise NotCached

    def _write_block_cache(self, block: np.ndarray, request: Request) -> None:
        sinks = list(self.sinks)
        if len(sinks) > 1:
            self._block_cache = block
            self._block_cache_position = request.loc.position
            self._block_cache_users = set(sinks)
            self._block_cache_users.remove(request.sink)

    def _use_block_cache(self, request: Request) -> None:
        self._block_cache_users.remove(request.sink)
        if not self._block_cache_users:
            self._block_cache = None

    def respond(self, request: Request) -> np.ndarray:
        try:
            result = self._read_block_cache(request)
        except NotCached:
            result = self._get_result(request)
            self._write_block_cache(result, request)
        else:
            self._use_block_cache(request)
        return result


class Event(Node, abc.ABC):
    pass


class Vis(Node, abc.ABC):
    pass
