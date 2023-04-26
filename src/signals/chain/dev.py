import abc
import queue
import sys
import typing

import attr as attr
import numpy as np
import sounddevice as sd

from signals import (
    SignalFlags,
)
from signals.chain import (
    BlockLoc,
    ExplicitChannels,
    Receiver,
    Request,
    Shape,
    Signal,
    port,
    state,
)
from signals.chain.files import (
    RecordingEmitter,
)


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

    @state
    class State(ExplicitChannels.State):
        # FIXME need more flexible validation because `channels` shouldn't be greater than self.info.max_channels
        pass

    def __init__(self, info: DeviceInfo):
        super().__init__(info=info)
        self.frame_position = 0
        self._stream = sd.OutputStream(device=self.info.index,
                                       callback=self._callback)

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.SINK_DEVICE

    @property
    def is_active(self) -> bool:
        return self._stream.active

    def start(self):
        self._stream.start()

    def stop(self):
        self._stream.stop()

    def seek(self, position: int):
        self.frame_position = position * self._stream.blocksize

    def tell(self) -> int:
        return self.frame_position / self._stream.blocksize

    def _callback(self, outdata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            self.log(status)
        shape = Shape(channels=self._state.channels, frames=frames)
        loc = BlockLoc(position=self.frame_position, shape=shape, rate=self._stream.samplerate)
        block = self.input.request(loc)
        outdata[:, :shape.channels] = block
        self.frame_position += frames

    def destroy(self) -> None:
        self._stream.close()
        super().destroy()


class SourceDevice(Device, RecordingEmitter):

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
