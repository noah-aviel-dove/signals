import abc
import collections
import enum
import inspect
import typing

import attr
import more_itertools
import numpy as np


class ChainLayerError(Exception):
    pass


def empty_response() -> np.ndarray:
    return np.zeros(shape=(1, 1))


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


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class BlockLoc:
    position: int
    shape: Shape

    @property
    def end_position(self) -> int:
        return self.position + self.shape[0]

    def resize(self, new_frames: int) -> typing.Self:
        if new_frames == self.shape.frames:
            return self
        else:
            return BlockLoc(position=self.position,
                            shape=Shape(frames=new_frames,
                                        channels=self.shape.channels))


SlotName = str


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Request:
    requestor: 'Signal'
    slot: SlotName
    loc: BlockLoc


class _Slot(property):
    pass


class BoundSlot:

    def __init__(self, parent: 'Signal', name: SlotName, sig: 'Signal' = None):
        self.name = name
        self.parent = parent
        self.sig = sig

    def __bool__(self):
        return self.sig is not None

    def _make_request(self, loc: BlockLoc) -> Request:
        return Request(requestor=self.parent, slot=self.name, loc=loc)

    def _do_request(self, request: Request) -> np.ndarray:
        block = self.sig.respond(request)
        assert block.shape <= request.loc.shape, (block.shape, request)
        return block

    def request(self, loc: BlockLoc) -> np.ndarray:
        if self.sig is None:
            return empty_response()
        else:
            return self._do_request(self._make_request(loc))

    def forward(self, request: Request, new_frames: int = None) -> np.ndarray:
        if self.sig is None:
            return empty_response()
        else:
            loc = (
                request.loc
                if new_frames is None else
                request.loc.resize(new_frames)
            )
            return self._do_request(self._make_request(loc))

    def forward_at_block_rate(self, request: Request) -> np.ndarray:
        return self.forward(request, 1)


class _Control(property):
    pass


class SignalType(enum.Enum):
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


# FIXME this should include arrays, I think
SigStateValue = float | int | bool | str
SigState = dict[str, SigStateValue]


class Signal(abc.ABC):

    def __init__(self):
        self._outputs: set[tuple[SlotName, Signal]] = set()
        self._last_reqest: typing.Optional[Request] = None
        self.enabled: bool = True
        self._slots = {
            slot: BoundSlot(parent=self, name=slot)
            for slot in self.slot_names()
        }

    @property
    @abc.abstractmethod
    def type(self) -> SignalType:
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
    def slot_names(cls) -> list[SlotName]:
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
    def inputs(self) -> typing.AbstractSet['Signal']:
        return {
            slot.value
            for slot in self._slots
        }

    @property
    def outputs(self) -> typing.AbstractSet['Signal']:
        return {
            sig
            for slot, sig in self._outputs
        }

    @property
    def inputs_by_slot(self) -> dict[SlotName, 'Signal']:
        return {
            slot.name: slot.sig
            for slot in self._slots.values()
            if slot
        }

    @property
    def outputs_with_slots(self) -> typing.AbstractSet[tuple[SlotName, 'Signal']]:
        # FIXME
        return self._outputs

    def upstream(self) -> typing.Sequence['Signal']:
        return self._upstream(set())

    def _upstream(self, visited: set['Signal']) -> collections.deque['Signal']:
        result = collections.deque()
        for input in self.inputs:
            if input not in visited:
                result.extend(input._upstream(visited))
                visited.update(result)
        assert self not in visited, 'Cycle detected'
        result.append(self)
        return result

    def respond(self, request: Request) -> np.ndarray:
        self._last_reqest = request
        return self._get_result(request)

    def destroy(self) -> None:
        for slot in self._slots:
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

    @property
    def cls_name(self) -> str:
        type_ = type(self)
        return f'{type_.__module__}.{type_.__qualname__}'

    def to_json(self) -> tuple[str, dict]:
        return self.cls_name, self.get_state()

    def get_state(self) -> SigState:
        return dict(
            enabled=self.enabled
        )

    def set_state(self, state: SigState) -> None:
        # FIXME need to validate values
        ks = state.keys() - self.get_state().keys()
        if ks:
            raise KeyError(*ks)
        for k, v in state.items():
            setattr(self, k, v)

    @classmethod
    def create(cls, cls_qualname: str) -> 'Signal':
        try:
            module_qualname, cls_name = cls_qualname.rsplit('.', 1)
        except ValueError:
            raise ImportError('Signal name must include a "."')
        module = __import__(module_qualname)
        _, *submodules = module_qualname.split('.')
        for attrib in submodules:
            module = getattr(module, attrib)
        try:
            target_cls = getattr(module, cls_name)
        except AttributeError as e:
            raise ImportError(*e.args)
        if isinstance(target_cls, type) and issubclass(target_cls, cls):
            if inspect.isabstract(target_cls):
                raise ImportError(f'{cls_qualname} is abstract')
            else:
                return target_cls()
        else:
            raise ImportError(f'{cls_qualname!r} is not a signal')


def slot(name: SlotName) -> _Slot:
    def fget(self: Signal) -> BoundSlot:
        return self._slots[name]

    def fdel(self: Signal) -> None:
        slot = fget(self)
        slot.sig._outputs.remove((name, self))
        slot.sig = None

    def fset(self: Signal, input: Signal) -> None:
        slot = fget(self)
        if slot.sig is not None:
            slot.sig._outputs.remove((name, self))
        slot.sig = input
        slot.sig._outputs.add((name, self))

    return _Slot(fget=fget, fset=fset, fdel=fdel)


class PassThroughShape(Signal, abc.ABC):

    @property
    def channels(self) -> int:
        input_shape = {input.channels for input in self.inputs}
        if len(input_shape) > 1:
            input_shape.discard(1)
        return more_itertools.one(input_shape)


class NotCached(RuntimeError):
    pass


class BlockCachingSignal(Signal, abc.ABC):

    def __init__(self):
        super().__init__()
        self._block_cache: np.ndarray | None = None
        self._block_cache_position: int | None = None
        self._block_cache_users: set[tuple[SlotName, Signal]] | None = None

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
            self._block_cache_users = self._outputs - {(request.slot, request.requestor)}

    def _use_block_cache(self, request: Request) -> None:
        self._block_cache_users.remove((request.slot, request.requestor))
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


class Event(Signal, abc.ABC):
    pass


class Vis(Signal, abc.ABC):
    pass
