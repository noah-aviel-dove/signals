import abc
import functools
import json
import re
import string
import typing

import attr
import bijection

from signals.chain import (
    SigStateValue,
    Signal,
    SignalName,
    SlotName,
)
import signals.chain.dev
import signals.chain.discovery

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
    v: SigStateValue

    @classmethod
    def parse(cls, item: str) -> typing.Self:
        k, v = item.split('=', 1)
        return cls(k=k, v=json.loads(v))

    def __str__(self) -> str:
        return f'{self.k}={json.dumps(self.v)}'


class SigState(signals.chain.SigState):

    def items(self):
        return (SigStateItem(k=k, v=v) for k, v in super().items())

    def __str__(self) -> str:
        return ' '.join(sorted(
            str(item)
            for item in self.items())
        )


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class MappedSigInfo:
    at: Coordinates
    cls_name: SignalName
    state: SigState

    @functools.cached_property
    def _sig_cls(self) -> type[signals.chain.Signal]:
        try:
            return signals.chain.discovery.load_signal(self.cls_name)
        except signals.chain.discovery.BadSignal as e:
            raise BadSignal(self.at, self.cls_name, e.args[0])

    def slot_names(self) -> list[signals.chain.SlotName]:
        return self._sig_cls.slot_names()

    def create(self) -> signals.chain.Signal:
        return self._sig_cls()


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class SlotInfo:
    at: Coordinates
    slot: SlotName

    @classmethod
    def parse(cls, slot: str) -> typing.Self:
        node_at, slot = slot.split('.')
        return cls(at=Coordinates.parse(node_at), slot=slot)

    def __str__(self) -> str:
        return f'{self.at}.{self.slot}'


@attr.s(auto_attribs=True, kw_only=True, frozen=True)
class ConnectionInfo:
    input_at: Coordinates
    output: SlotInfo


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


class MapLayerError(Exception):

    def __str__(self) -> str:
        return ' '.join((type(self).__name__, *self.args))


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

    def __init__(self, slot: SlotInfo):
        super().__init__(slot.at, f'Slot {slot.slot!r} has no input.')


class AlreadyConnected(MapError):

    def __init__(self, connection: ConnectionInfo):
        slot = connection.output
        super().__init__(slot.at, f'Slot {slot.slot!r} already has input at {connection.input_at}')


class BadSignal(MapError):

    def __init__(self, at: Coordinates, signal: str, reason: str):
        super().__init__(at,
                         f'Failed to load "{signal}":',
                         reason)


class BadName(Exception, abc.ABC):

    def __init__(self, *args, options=()):
        super().__init__(*args, 'Valid options are:', ', '.join(sorted(map(repr, options))))


class BadSlot(BadName, MapError):

    def __init__(self, slot: SlotInfo, signal: Signal):
        super().__init__(slot.at,
                         f'{signal.cls_name} has no slot {slot.slot!r}.',
                         options=signal.slot_names())


class BadProperty(BadName, MapError):

    def __init__(self, at: Coordinates, signal: Signal, prop: str):
        super().__init__(at,
                         f'{signal.cls_name} has no property {prop!r}.',
                         options=signal.get_state().keys())


class Map:

    def __init__(self):
        self._map = bijection.Bijection[Coordinates, Signal]()

    def new(self) -> typing.Self:
        return type(self)()

    def add(self, info: MappedSigInfo):
        sig = info.create()
        self._set_state(info.at, sig, info.state)
        # This is a weird smell. Perhaps we could populate a complete state when
        # the command is created?
        info.state.update(sig.get_state())
        if self._map.setdefault(info.at, sig) is not sig:
            raise NonEmpty(info.at)

    def rm(self, at: Coordinates) -> LinkedSigInfo:
        sig = self._pop(at)
        inputs = list(self._find_inputs(at, sig))
        outputs = list(self._find_outputs(at, sig))
        state = SigState(sig.get_state())
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
                                   cls_name=sig.cls_name,
                                   state=SigState(sig.get_state()),
                                   links_in=inputs,
                                   links_out=outputs)
        for connection in result.links:
            assert self.disconnect(connection.output) == connection.input_at, connection
        sig.destroy()
        return result

    def edit(self, at: Coordinates, state: SigState) -> SigState:
        sig = self._find(at)
        old_state = SigState(sig.get_state())
        self._set_state(at, sig, state)
        return old_state

    def mv(self, at1: Coordinates, at2: Coordinates) -> None:
        v1 = self._pop(at1)
        if (v2 := self._map.pop(at2, None)) is not None:
            self._map[at1] = v2
        self._map[at2] = v1

    def connect(self, info: ConnectionInfo) -> Coordinates | None:
        input_sig = self._find(info.input_at)
        output_sig = self._find(info.output.at)
        old_input_slot = getattr(output_sig, info.output.slot)
        old_input_at = self._map.inv[old_input_slot.sig] if old_input_slot else None
        if old_input_at == info.input_at:
            raise AlreadyConnected(info)
        else:
            try:
                # FIXME this does not raise a KeyError if the slot name is invalid
                #  i think I need actual setters instead of using setattr
                setattr(output_sig, info.output.slot, input_sig)
            except KeyError:
                raise BadSlot(info.output, output_sig)
            else:
                return old_input_at

    def disconnect(self, slot_info: SlotInfo) -> Coordinates:
        output = self._find(slot_info.at)
        try:
            input = getattr(output, slot_info.slot).sig
        except KeyError:
            raise BadSlot(slot_info, output)
        else:
            if input is None:
                raise NotConnected(slot_info)
            else:
                # this may fail if the input is outside the map
                # e.g. if we only map a subset of the graph
                input_at = self._map.inv[input]
                delattr(output, slot_info.slot)
                return input_at

    def iter_signals(self) -> typing.Iterator[MappedSigInfo]:
        for at, sig in self._map.items():
            if not isinstance(sig, signals.chain.dev.Device):
                yield MappedSigInfo(at=at,
                                    cls_name=sig.cls_name,
                                    state=SigState(sig.get_state()))

    def iter_connections(self) -> typing.Iterator[ConnectionInfo]:
        for at, sig in self._map.items():
            for slot, input_sig in sig.inputs_by_slot.items():
                yield ConnectionInfo(input_at=self._map.inv[input_sig],
                                     output=SlotInfo(at=at, slot=slot))

    def iter_sources(self) -> typing.Iterator[MappedDevInfo]:
        for at, sig in self._map.items():
            if isinstance(sig, signals.chain.dev.SourceDevice):
                yield MappedDevInfo.for_source(at=at,
                                               device=sig.info,
                                               state=SigState(sig.get_state()))

    def iter_sinks(self) -> typing.Iterator[MappedDevInfo]:
        for at, sig in self._map.items():
            if isinstance(sig, signals.chain.dev.SinkDevice):
                yield MappedDevInfo.for_source(at=at,
                                               device=sig.info,
                                               state=SigState(sig.get_state()))

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

    def _set_state(self, at: Coordinates, signal: Signal, state: SigState):
        try:
            signal.set_state(state)
        except KeyError as e:
            raise BadProperty(at, signal, e.args[0])

    def _find_inputs(self, at: Coordinates, signal: Signal) -> typing.Iterator[ConnectionInfo]:
        for slot in signal.slot_names():
            if input := getattr(signal, slot):
                slot_info = SlotInfo(at=at, slot=slot)
                input_at = self._map.inv[input]
                yield ConnectionInfo(input_at=input_at, output=slot_info)

    def _find_outputs(self, at: Coordinates, signal: Signal) -> typing.Iterator[ConnectionInfo]:
        for slot, output_sig in signal.outputs_with_slots:
            output_at = self._map.inv[output_sig]
            slot_info = SlotInfo(at=output_at, slot=slot)
            yield ConnectionInfo(input_at=at, output=slot_info)
