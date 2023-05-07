import abc
import queue
import sys
import traceback
import typing

import attr as attr
import attrs.validators
import numpy as np
import sounddevice as sd

from signals import (
    SignalFlags,
)
from signals.chain import (
    BlockLoc,
    ChainLayerError,
    Emitter,
    ExplicitChannels,
    Receiver,
    Request,
    Shape,
    Signal,
    port,
    state,
)


class BadPlaybackState(ChainLayerError):
    pass


@attr.s(auto_attribs=True, frozen=True, kw_only=True, order=False)
class DeviceInfo:
    name: str
    index: int
    hostapi: int
    max_input_channels: int
    max_output_channels: int
    default_low_input_latency: float
    default_low_output_latency: float
    default_high_input_latency: float
    default_high_output_latency: float
    default_samplerate: float

    @property
    def is_source(self) -> bool:
        return self.max_input_channels > 0

    @property
    def is_sink(self) -> bool:
        return self.max_output_channels > 0

    def __str__(self) -> str:
        latency_low = self._format_latency(self.default_low_input_latency, self.default_low_output_latency)
        latency_high = self._format_latency(self.default_high_input_latency, self.default_low_output_latency)
        return '\n'.join((
            f'{self.index:<3} {self.name} ({self.hostapi})',
            f'\tMaximum supported channels (I/O): {self.max_input_channels}/{self.max_output_channels}',
            f'\tDefault samplerate: {self.default_samplerate}',
            f'\tDefault interactive latency{latency_low}',
            f'\tDefault non-interactive latency{latency_high}'
        ))

    def _format_latency(self, input: float, output: float) -> str:
        if input != output and self.is_source and self.is_sink:
            result = f' (I/O): {input:.05}/{output:.05}'
        elif self.is_source:
            result = f': {input:.05}'
        elif self.is_sink:
            result = f': {output:.05}'
        else:
            assert False, self
        return result

    def __lt__(self, other: typing.Self) -> bool:
        return self.index < other.index


class Device(Signal, abc.ABC):

    def __init__(self, info: DeviceInfo):
        super().__init__()
        self.info = info

    def log(self, msg: typing.Any) -> None:
        print(msg, sys.stderr)


class SinkDevice(Device, Receiver, ExplicitChannels):
    # FIXME this should support recording.
    #  Give `Recorder` an ABC that allows for more flexible buffer population
    #  (so it doesn't have to be written to during `respond`).
    input = port('input')

    def __init__(self, info: DeviceInfo):

        @state
        class State(ExplicitChannels.State):
            channels: int = attr.ib(default=1,
                                    validator=attrs.validators.in_(range(1, info.max_input_channels + 1)))

        self.State = State

        super().__init__(info=info)
        self.frame_position = 0
        self._stream: sd.OutputStream | None = None

    def set_state(self, new_state: 'SinkDevice.State') -> None:
        super().set_state(new_state)
        if self.is_open and self._stream.channels != new_state.channels:
            active = self.is_active
            self.close()
            if active:
                self.start()
            else:
                self.open()

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.SINK_DEVICE

    def destroy(self) -> None:
        if self.is_open:
            self.close()
        super().destroy()

    @property
    def is_open(self) -> bool:
        return self._stream is not None

    @property
    def is_active(self) -> bool:
        return self.is_open and self._stream.active

    def open(self) -> None:
        if self.is_open:
            raise BadPlaybackState('The output stream is already open')
        self._stream = sd.OutputStream(device=self.info.index,
                                       callback=self._callback,
                                       channels=self._state.channels)

    def close(self) -> None:
        if self.is_open:
            self._stream.close()
            self._stream = None
        else:
            raise BadPlaybackState('The output stream is not open')

    def start(self):
        if not self.is_open:
            self.open()
        self._stream.start()

    def stop(self):
        if self.is_active:
            self._stream.stop()
        else:
            raise BadPlaybackState('The output stream is not active')

    def seek(self, position: int):
        self.frame_position = position * self._stream.blocksize

    def tell(self) -> int:
        return self.frame_position // self._stream.blocksize

    def _callback(self, outdata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            self.log(status)
        shape = Shape(channels=self._state.channels, frames=frames)
        loc = BlockLoc(position=self.frame_position, shape=shape, rate=int(self._stream.samplerate))
        try:
            block = self.input.request(loc)
        except Exception:
            self.log(traceback.format_exc())
            raise sd.CallbackStop
        else:
            outdata[:, :shape.channels] = block
        self.frame_position += frames


class SourceDevice(Device, Emitter):

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self.q: queue.Queue[tuple[BlockLoc, np.ndarray]] = queue.Queue()
        self._stream = None
        self.position = 0

    @property
    def channels(self) -> int:
        return self.info.max_input_channels

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.SOURCE_DEVICE

    def _callback(self, indata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            self.log(status)
        if frames:
            old_position = self.position
            self.position += frames
            self.q.put((BlockLoc(position=old_position,
                                 shape=Shape.of_array(indata),
                                 rate=self._stream.samplerate),
                        # FIXME why is copy necessary?
                        indata.copy()))
        else:
            raise sd.CallbackStop

    def _start(self, request: Request) -> None:
        self._stream = sd.InputStream(device=self.info.index,
                                      callback=self._callback,
                                      blocksize=request.loc.shape.frames,
                                      samplerate=request.loc.rate)
        self._stream.start()

    def _get_result(self, request: Request) -> np.ndarray:
        if self._stream is None:
            self._start(request)

        if request.loc.shape.frames != self._stream.blocksize:
            raise NotImplementedError

        if request.loc.position % self._stream.blocksize != 0:
            raise NotImplementedError

        if request.loc.rate != self._stream.samplerate:
            raise NotImplementedError

        return super()._get_result(request)

    def _eval(self, request: Request) -> np.ndarray:
        max_position = self.position
        if request.loc.position > max_position:
            return np.zeros(Shape.unit())
        else:
            while True:
                loc, block = self.q.get()
                if loc == request.loc:
                    return block
                elif loc.position > request.loc.position:
                    raise RuntimeError
