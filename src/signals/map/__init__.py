import abc
import copy
import functools
import json
import re
import string
import typing

import attr
import bijection
import matplotlib.pyplot as plt
import numpy as np

from signals import (
    PortName,
    SigStateValue,
    SignalFlags,
    SignalsError,
)
from signals.chain import (
    Emitter,
    Receiver,
    Signal,
)
import signals.chain.dev
import signals.chain.discovery
import signals.chain.vis

CoordinateRow = int


class CoordinateColumn(int):

    def __new__(cls, value: int | str):
        if isinstance(value, str):
            i = 0
            alphabet_start = ord('a')
            for e, c in enumerate(reversed(value)):
                i += (ord(c) - alphabet_start + 1) * 26 ** e
            value = i
        if value <= 0:
            raise ValueError(value)
        return super().__new__(cls, value)

    def __str__(self):
        i = self
        digits = []
        while i:
            i, d = divmod(i - 1, 26)
            digits.append(d)
        return ''.join(string.ascii_lowercase[d] for d in reversed(digits))


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class Coordinates:
    row: CoordinateRow = attr.ib(validator=attr.validators.ge(1))
    col: CoordinateColumn = attr.ib(converter=CoordinateColumn)

    def __str__(self) -> str:
        """
        >>> str(Coordinates(row=1, col=1))
        '1a'
        >>> str(Coordinates(row=1, col=26))
        '1z'
        >>> str(Coordinates(row=1, col=27))
        '1aa'
        >>> str(Coordinates(row=1, col=52))
        '1az'
        >>> str(Coordinates(row=1, col=702))
        '1zz'
        >>> str(Coordinates(row=1234, col=1234))
        '1234aul'
        """
        return f'{self.row}{self.col}'

    _coord_re = re.compile(r'(\d+)([a-z]+)')

    @classmethod
    def parse(cls, s: str) -> typing.Self:
        """
        >>> Coordinates.parse('1a')
        Coordinates(row=1, col=1)
        >>> Coordinates.parse('1b')
        Coordinates(row=1, col=2)
        >>> Coordinates.parse('1z')
        Coordinates(row=1, col=26)
        >>> Coordinates.parse('1aa')
        Coordinates(row=1, col=27)
        >>> Coordinates.parse('1az')
        Coordinates(row=1, col=52)
        >>> Coordinates.parse('1zz')
        Coordinates(row=1, col=702)
        >>> Coordinates.parse('1234aul')
        Coordinates(row=1234, col=1234)
        """
        match = re.fullmatch(cls._coord_re, s)
        if match:
            row, col = match.groups()
            return cls(row=int(row), col=CoordinateColumn(col))
        else:
            raise ValueError(s)


class SigStateItem(typing.NamedTuple):
    k: str
    v: signals.SigStateValue

    @classmethod
    def parse(cls, item: str) -> typing.Self:
        """
        >>> s = SigStateItem.parse('foo=1')
        >>> s
        SigStateItem(k='foo', v=1)
        >>> str(s)
        'foo=1'

        >>> s = SigStateItem.parse('bar=[[1, 2, 3]]')
        >>> s
        SigStateItem(k='bar', v=array([[1, 2, 3]]))
        >>> str(s)
        'bar=[[1, 2, 3]]'
        """
        k, v = item.split('=', 1)
        v = cls.parse_value(v)
        return cls(k=k, v=v)

    def __str__(self) -> str:
        return f'{self.k}={self.dump_value(self.v)}'

    @classmethod
    def parse_value(cls, v: str) -> signals.SigStateValue:
        try:
            v = json.loads(v)
        except ValueError:
            pass
        else:
            if isinstance(v, list):
                v = np.array(v)
        return v

    @classmethod
    def dump_value(cls, v: SigStateValue) -> str:
        if isinstance(v, str):
            return v
        else:
            if isinstance(v, np.ndarray):
                v = v.tolist()
            return json.dumps(v)


class SigStateItems(tuple[SigStateItem]):

    def __str__(self) -> str:
        return ' '.join(map(str, self))


class SigState(dict[str, SigStateValue]):

    def items(self) -> SigStateItems:
        items = SigStateItems(SigStateItem(k=k, v=v) for k, v in super().items())
        return items

    @classmethod
    def from_signal(cls, signal: signals.chain.Signal) -> typing.Self:
        return cls(attr.asdict(signal.get_state()))

    def __str__(self) -> str:
        return str(self.items())


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class MappedSigInfo:
    at: Coordinates
    cls_name: str
    state: SigState

    def __attrs_post_init__(self):
        all_keys = self.state_attr_names()
        missing = all_keys ^ self.state.keys()
        default_state = self._sig_cls.State()
        for k in missing:
            try:
                v = getattr(default_state, k)
            except AttributeError:
                raise BadProperty(self.at, self.create(), k)
            else:
                self.state[k] = v
        assert self.state.keys() == all_keys, (all_keys, self.state)

    @functools.cached_property
    def _sig_cls(self) -> type[signals.chain.Signal]:
        try:
            return signals.chain.discovery.load_signal(self.cls_name)
        except signals.chain.discovery.BadSignal as e:
            raise BadSignal(self.at, self.cls_name, e.args[0])

    def port_names(self) -> list[signals.chain.PortName]:
        if issubclass(self._sig_cls, Receiver):
            return self._sig_cls.port_names()
        else:
            return []

    def state_attr_names(self) -> typing.AbstractSet[str]:
        return self._sig_cls.state_attrs()

    @property
    def flags(self) -> SignalFlags:
        return self._sig_cls.flags()

    def create(self) -> signals.chain.Signal:
        return self._sig_cls()


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class PortInfo:
    at: Coordinates
    port: PortName

    @classmethod
    def parse(cls, port: str) -> typing.Self:
        node_at, port = port.split('.')
        return cls(at=Coordinates.parse(node_at), port=port)

    def __str__(self) -> str:
        return f'{self.at}.{self.port}'


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class ConnectionInfo:
    input_at: Coordinates
    output: PortInfo


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class LinkedSigInfo(MappedSigInfo):
    links_in: typing.Collection[ConnectionInfo]
    links_out: typing.Collection[ConnectionInfo]

    @property
    def links(self) -> typing.Iterator[ConnectionInfo]:
        yield from self.links_in
        yield from self.links_out


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class MappedDevInfo(MappedSigInfo):
    device: signals.chain.dev.DeviceInfo

    _source_cls_name = 'signals.chain.dev.SourceDevice'
    _sink_cls_name = 'signals.chain.dev.SinkDevice'

    @classmethod
    def for_source(cls,
                   *,
                   device: signals.chain.dev.DeviceInfo,
                   at: Coordinates,
                   state: SigState = None
                   ) -> typing.Self:
        return cls(cls_name=cls._source_cls_name,
                   state=SigState() if state is None else state,
                   device=device,
                   at=at)

    @classmethod
    def for_sink(cls,
                 *,
                 device: signals.chain.dev.DeviceInfo,
                 at: Coordinates,
                 state: SigState = None
                 ) -> typing.Self:
        return cls(cls_name=cls._sink_cls_name,
                   state=SigState() if state is None else state,
                   device=device,
                   at=at)

    def create(self) -> signals.chain.Signal:
        return self._sig_cls(self.device)


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class LinkedDevInfo(MappedDevInfo, LinkedSigInfo):

    @classmethod
    def for_linked_source(cls,
                          *,
                          device: signals.chain.dev.DeviceInfo,
                          at: Coordinates,
                          state: SigState = None,
                          links_out: typing.Collection[ConnectionInfo]
                          ) -> typing.Self:
        return cls(cls_name=cls._source_cls_name,
                   device=device,
                   at=at,
                   state=state,
                   links_out=links_out,
                   links_in=())

    @classmethod
    def for_linked_sink(cls,
                        *,
                        device: signals.chain.dev.DeviceInfo,
                        at: Coordinates,
                        state: SigState = None,
                        links_in: typing.Collection[ConnectionInfo]
                        ) -> typing.Self:
        return cls(cls_name=cls._sink_cls_name,
                   device=device,
                   at=at,
                   state=state,
                   links_out=(),
                   links_in=links_in)


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class PlaybackState:
    position: int | None
    active: bool | None


class MapLayerError(SignalsError):
    pass


class MapError(MapLayerError):

    def __init__(self, at: Coordinates, *args: str):
        super().__init__(f'at {at}:', *args)


class Empty(MapError):

    def __init__(self, at: Coordinates):
        super().__init__(at, 'Coordinates are empty')


class NonEmpty(MapError):

    def __init__(self, at: Coordinates):
        super().__init__(at, 'Coordinates are not empty')


class NotConnected(MapError):

    def __init__(self, port: PortInfo):
        super().__init__(port.at, f'Port {port.port!r} has no input.')


class AlreadyConnected(MapError):

    def __init__(self, connection: ConnectionInfo):
        port = connection.output
        super().__init__(port.at, f'Port {port.port!r} already has input at {connection.input_at}')


class BadSignal(MapError):

    def __init__(self, at: Coordinates, signal: str, reason: str):
        super().__init__(at,
                         f'Failed to load "{signal}":',
                         reason)


class BadName(Exception, abc.ABC):

    def __init__(self, *args, options=()):
        super().__init__(*args, 'Valid options are:', ', '.join(sorted(map(repr, options))))


class BadPort(BadName, MapError):

    def __init__(self, port: PortInfo, signal: Receiver):
        super().__init__(port.at,
                         f'{signal.cls_name} has no port {port.port!r}.',
                         options=signal.port_names())


class BadProperty(BadName, MapError):

    def __init__(self, at: Coordinates, signal: Signal, prop: str):
        super().__init__(at,
                         f'{signal.cls_name()} has no property {prop!r}.',
                         options=signal.state_attrs())


class BadSignalClass(MapError):
    def __init__(self, at: Coordinates, signal: Signal, expected):
        super().__init__(at, f'{signal.cls_name!r} is not a {expected.__name__}')


class BadReceiver(BadSignalClass):
    def __init__(self, at: Coordinates, signal: Signal):
        super().__init__(at, signal, Receiver)


class BadPlaybackTarget(BadSignalClass):
    def __init__(self, at: Coordinates, signal: Signal):
        super().__init__(at, signal, signals.chain.dev.SinkDevice)


class BadVis(BadSignalClass):
    def __init__(self, at: Coordinates, signal: Signal):
        super().__init__(at, signal, signals.chain.vis.Vis)


class Map:

    def __init__(self):
        self._map = bijection.Bijection[Coordinates, Signal]()

    def add(self, info: MappedSigInfo):
        sig = info.create()
        self._apply_state(info.at, sig, info.state)
        if self._map.setdefault(info.at, sig) is not sig:
            raise NonEmpty(info.at)

    def rm(self, at: Coordinates) -> LinkedSigInfo:
        sig = self._find(at)

        state = SigState.from_signal(sig)
        inputs = []
        outputs = []
        if isinstance(sig, Emitter):
            for port, output_sig in tuple(sig.outputs_with_ports):
                output_at = self._map.inv[output_sig]
                port_info = PortInfo(at=output_at, port=port)
                self.disconnect(port_info)
                con_info = ConnectionInfo(input_at=at, output=port_info)
                outputs.append(con_info)
        if isinstance(sig, Receiver):
            for port_name, input_sig in tuple(sig.inputs_by_port.items()):
                port_info = PortInfo(at=at, port=port_name)
                self.disconnect(port_info)
                input_at = self._map.inv[input_sig]
                con_info = ConnectionInfo(input_at=input_at, output=port_info)
                inputs.append(con_info)

        sig.destroy()
        self._map.inv.pop(sig)

        if isinstance(sig, signals.chain.dev.SourceDevice):
            assert not inputs, inputs
            result = LinkedDevInfo.for_linked_source(at=at,
                                                     state=state,
                                                     links_out=outputs,
                                                     device=sig.info)
        elif isinstance(sig, signals.chain.dev.SinkDevice):
            assert not outputs, outputs
            result = LinkedDevInfo.for_linked_sink(at=at,
                                                   state=state,
                                                   links_in=inputs,
                                                   device=sig.info)
        else:
            result = LinkedSigInfo(at=at,
                                   cls_name=sig.cls_name(),
                                   state=state,
                                   links_in=inputs,
                                   links_out=outputs)

        return result

    def edit(self, at: Coordinates, state: SigState) -> SigState:
        sig = self._find(at)
        old_state = SigState.from_signal(sig)
        self._apply_state(at, sig, state)
        return old_state

    def mv(self, at1: Coordinates, at2: Coordinates) -> None:
        v1 = self._pop(at1)
        if (v2 := self._map.pop(at2, None)) is not None:
            self._map[at1] = v2
        self._map[at2] = v1

    def connect(self, info: ConnectionInfo) -> Coordinates | None:
        input_sig = self._find(info.input_at)
        output_sig = self._find(info.output.at)
        old_input_port = getattr(output_sig, info.output.port)
        old_input_at = self._map.inv[old_input_port.sig] if old_input_port else None
        if old_input_at == info.input_at:
            raise AlreadyConnected(info)
        elif isinstance(output_sig, Receiver):
            try:
                # FIXME this does not raise a KeyError if the part name is invalid
                #  i think I need actual setters instead of using setattr
                setattr(output_sig, info.output.port, input_sig)
            except KeyError:
                raise BadPort(info.output, output_sig)
            else:
                return old_input_at
        else:
            raise BadReceiver(info.output.at, output_sig)

    def disconnect(self, info: PortInfo) -> Coordinates:
        output = self._find(info.at)
        try:
            input = getattr(output, info.port).sig
        except KeyError:
            if isinstance(output, Receiver):
                raise BadPort(info, output)
            else:
                raise BadReceiver(info.at, output)
        else:
            if input is None:
                raise NotConnected(info)
            else:
                # this may fail if the input is outside the map
                # e.g. if we only map a subset of the graph
                input_at = self._map.inv[input]
                delattr(output, info.port)
                return input_at

    def playback(self, at: Coordinates, state: PlaybackState) -> None:
        sink = self._find(at)
        if isinstance(sink, signals.chain.dev.SinkDevice):
            if state.position is not None:
                sink.seek(state.position)
            if state.active is not None:
                if state.active:
                    sink.start()
                else:
                    sink.stop()
        else:
            raise BadPlaybackTarget(at, sink)

    def iter_signals(self) -> typing.Iterator[MappedSigInfo]:
        for at, sig in self._map.items():
            if not isinstance(sig, signals.chain.dev.Device):
                yield MappedSigInfo(at=at,
                                    cls_name=sig.cls_name(),
                                    state=SigState.from_signal(sig))

    def iter_connections(self) -> typing.Iterator[ConnectionInfo]:
        for at, sig in self._map.items():
            if isinstance(sig, Receiver):
                for port, input_sig in sig.inputs_by_port.items():
                    yield ConnectionInfo(input_at=self._map.inv[input_sig],
                                         output=PortInfo(at=at, port=port))

    def iter_sources(self) -> typing.Iterator[MappedDevInfo]:
        for at, sig in self._map.items():
            if isinstance(sig, signals.chain.dev.SourceDevice):
                yield MappedDevInfo.for_source(at=at,
                                               device=sig.info,
                                               state=SigState.from_signal(sig))

    def iter_sinks(self) -> typing.Iterator[MappedDevInfo]:
        for at, sig in self._map.items():
            if isinstance(sig, signals.chain.dev.SinkDevice):
                yield MappedDevInfo.for_sink(at=at,
                                             device=sig.info,
                                             state=SigState.from_signal(sig))

    def render(self, at: Coordinates, ax: plt.Axes, frames: int) -> list[plt.Artist]:
        sig = self._find(at)
        if isinstance(sig, signals.chain.vis.Vis):
            return sig.render(ax, frames)
        else:
            raise BadVis(at, sig)

    def _find(self, at: Coordinates) -> Signal:
        try:
            return self._map[at]
        except KeyError:
            raise Empty(at)

    def _pop(self, at: Coordinates) -> Signal:
        try:
            return self._map.pop(at)
        except KeyError:
            raise Empty(at)

    def _apply_state(self, at: Coordinates, signal: Signal, state: SigState):
        new_state = copy.copy(signal.get_state())
        for k, v in state.items():
            try:
                setattr(new_state, k, v)
            except AttributeError:
                raise BadProperty(at, signal, k)
            except signals.chain.BadStateValue:
                raise
        signal.set_state(new_state)
