import abc
import collections
import enum
import functools
import itertools
import typing

import attr
import more_itertools
import numpy as np

from signals import (
    PortName,
    SignalFlags,
    SignalsError,
)
import signals.discovery


class ChainLayerError(SignalsError):
    pass


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

    @classmethod
    def unit(cls) -> typing.Self:
        return Shape(frames=1, channels=1)

    def __le__(self, other: tuple[int, int]) -> bool:
        return (self[0] in (1, other[0])) and (self[1] in (1, other[1]))

    def __ge__(self, other: tuple[int, int]) -> bool:
        return (other[0] in (1, self[0])) and (other[1] in (1, self[1]))

    @classmethod
    def of_array(cls, array: np.ndarray) -> typing.Self:
        return cls(*array.shape)


class BadShape(ChainLayerError):

    def __init__(self, source: 'Signal', shape: tuple, constraint: tuple):
        super().__init__(f'Invalid response from {source.cls_name()!r}): '
                         f'Block with shape {shape} incompatible with requested shape {constraint}')


class BadStateSchema(ChainLayerError):

    def __init__(self, sig: 'Signal', state: 'Signal.State'):
        super().__init__(f'Signal {sig.cls_name()!r} cannot accept state of type {state.cls_name()!r}')


class BadStateValue(ChainLayerError):

    def __init__(self, state: 'Signal.State', key: str, value: typing.Any, reason: typing.Any = None):
        reason = '' if reason is None else f': ({reason})'
        super().__init__(f'Value {value!r} is invalid for property {key!r} in schema {state.cls_name()!r}{reason}')


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class BlockLoc:
    position: int
    rate: int
    shape: Shape

    @property
    def end_position(self) -> int:
        return self.position + self.shape[0]

    @property
    def timestamp(self) -> float:
        return self.position / self.rate

    @functools.cached_property
    def frame_range(self) -> np.ndarray:
        frames = np.arange(self.position, self.end_position).reshape(-1, 1)
        frames.flags.writeable = False
        return frames

    def resize(self, new_frames: int) -> typing.Self:
        if new_frames == self.shape.frames:
            return self
        else:
            return attr.evolve(self, shape=Shape(frames=new_frames,
                                                 channels=self.shape.channels))


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Request:
    requestor: 'Receiver'
    port: PortName
    loc: BlockLoc


class _Port(property):
    pass


class RequestRate(enum.Enum):
    UNKNOWN = enum.auto()
    BLOCK = enum.auto()
    FRAME = enum.auto()
    UNUSED_FRAME = enum.auto()


state = attr.s(auto_attribs=True, frozen=False, kw_only=True, slots=True)


class Signal(abc.ABC, signals.discovery.Named):
    @state
    class State(signals.discovery.Named):
        pass

    def __init__(self):
        self._state = self.State()

    @classmethod
    @abc.abstractmethod
    def flags(cls) -> SignalFlags:
        return SignalFlags(0)

    @classmethod
    def state_attrs(cls) -> set[str]:
        slots = set(itertools.chain.from_iterable(
            getattr(cls_, '__slots__', ())
            for cls_ in cls.State.mro())
        )
        slots.discard('__weakref__')
        return slots

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, new_state: State) -> None:
        if not isinstance(new_state, self.State):
            raise BadStateSchema(self, new_state)
        self._state = new_state

    def destroy(self) -> None:
        pass


class Emitter(Signal, abc.ABC):
    @state
    class State(Signal.State):
        enabled: bool = attr.ib(default=True)

    def __init__(self):
        super().__init__()
        self._outputs: set[tuple[PortName, Receiver]] = set()
        self._last_request: typing.Optional[Request] = None

    @property
    def outputs_with_ports(self) -> typing.AbstractSet[tuple[PortName, 'Receiver']]:
        return self._outputs

    @property
    def rate(self) -> RequestRate:
        if self._last_request is None:
            return RequestRate.UNKNOWN
        else:
            frames = self._last_request.loc.shape.frames
            if frames <= 0:
                return RequestRate.UNKNOWN
            elif frames == 1:
                return RequestRate.BLOCK
            else:
                return RequestRate.FRAME

    @property
    @abc.abstractmethod
    def channels(self) -> int:
        raise NotImplementedError

    @abc.abstractmethod
    def _eval(self, request: Request) -> np.ndarray:
        raise NotImplementedError

    @classmethod
    def empty_result(cls) -> np.ndarray:
        return np.zeros(Shape.unit())

    def _get_result(self, request: Request) -> np.ndarray:
        return self._eval(request) if self._state.enabled else self.empty_result()

    def respond(self, request: Request) -> np.ndarray:
        self._last_request = request
        return self._get_result(request)

    def destroy(self) -> None:
        super().destroy()
        for port_name, receiver in tuple(self.outputs_with_ports):
            delattr(receiver, port_name)


class Receiver(Signal, abc.ABC):
    class BoundPort:

        def __init__(self, parent: 'Receiver', name: PortName, emitter: 'Emitter' = None):
            self.name = name
            self.parent = parent
            self.sig = emitter

        def expel(self) -> None:
            self.sig._outputs.remove((self.name, self.parent))
            self.sig = None

        def assign(self, input_: 'Signal') -> None:
            if self.sig is not None:
                self.expel()
            self.sig = input_
            self.sig._outputs.add((self.name, self.parent))

        def __bool__(self):
            return self.sig is not None

        def _make_request(self, loc: BlockLoc) -> Request:
            return Request(requestor=self.parent, port=self.name, loc=loc)

        def _do_request(self, request: Request) -> np.ndarray:
            block = self.sig.respond(request)
            if not (block.shape <= request.loc.shape):
                raise BadShape(self.sig, block.shape, request.loc.shape)
            return block

        def request(self, loc: BlockLoc) -> np.ndarray:
            if self.sig is None:
                return Emitter.empty_result()
            else:
                return self._do_request(self._make_request(loc))

        def forward(self, request: Request) -> np.ndarray:
            return self.request(request.loc)

        def forward_at_block_rate(self, request: Request) -> np.ndarray:
            return self.request(request.loc.resize(1))

    def __init__(self):
        super().__init__()
        self._ports = {
            port: self.BoundPort(parent=self, name=port)
            for port in self.port_names()
        }

    @classmethod
    def port_names(cls) -> list[PortName]:
        return [
            k
            for k in dir(cls)
            if isinstance(getattr(cls, k), _Port)
        ]

    @property
    def inputs_by_port(self) -> dict[PortName, 'Emitter']:
        return {
            port.name: port.sig
            for port in self._ports.values()
            if port
        }

    def upstream(self) -> typing.Sequence['Emitter']:
        return self._upstream(set())

    def _upstream(self, visited: set['Emitter']) -> collections.deque['Emitter']:
        result = collections.deque()
        for input in self.inputs_by_port.values():
            if input not in visited and isinstance(input, Receiver):
                result.extend(input._upstream(visited))
                visited.update(result)
        assert self not in visited, 'Cycle detected'
        result.append(self)
        return result

    def destroy(self) -> None:
        super().destroy()
        for port_name, bound_port in tuple(self._ports.items()):
            if bound_port:
                delattr(self, port_name)


def port(name: PortName) -> _Port:
    def fget(self: Receiver) -> Receiver.BoundPort:
        return self._ports[name]

    def fdel(self: Receiver) -> None:
        self._ports[name].expel()

    def fset(self: Receiver, input_: Emitter) -> None:
        self._ports[name].assign(input_)

    return _Port(fget=fget, fset=fset, fdel=fdel)


class PassThroughShape(Receiver, Emitter, abc.ABC):

    @property
    def channels(self) -> int:
        input_shape = {
            input.channels
            for input in self.inputs_by_port.values()
        }
        if len(input_shape) > 1:
            input_shape.discard(1)
        return more_itertools.one(input_shape)


class NotCached(RuntimeError):
    pass


class BlockCachingEmitter(Emitter, abc.ABC):

    def __init__(self):
        super().__init__()
        self._block_cache: np.ndarray | None = None
        self._block_cache_position: int | None = None
        self._block_cache_users: set[tuple[PortName, Receiver]] | None = None

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
        if len(self._outputs) > 1:
            self._block_cache = block
            self._block_cache_position = request.loc.position
            self._block_cache_users = self._outputs - {(request.port, request.requestor)}

    def _use_block_cache(self, request: Request) -> None:
        self._block_cache_users.remove((request.port, request.requestor))
        if not self._block_cache_users:
            self._block_cache = None

    def respond(self, request: Request) -> np.ndarray:
        try:
            result = self._read_block_cache(request)
        except NotCached:
            result = super().respond(request)
            self._write_block_cache(result, request)
        else:
            self._use_block_cache(request)
        return result


if False:
    class Epoch(Signal, abc.ABC):

        @classmethod
        def flags(cls) -> SignalFlags:
            return super().flags() | SignalFlags.EPOCH


    class Vis(Signal, abc.ABC):

        @classmethod
        def flags(cls) -> SignalFlags:
            return super().flags() | SignalFlags.VIS
