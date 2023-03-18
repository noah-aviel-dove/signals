import abc
import queue
import sys
import threading
import typing

import attr as attr
import numpy as np
import sounddevice as sd

from signals.chain import (
    BlockLoc,
    Request,
    Shape,
    Signal,
    SignalType,
    slot,
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
        return '\n'.join((
            f'{self.index:<3} {self.name} ({self.hostapi})',
            f'\tMaximum supported channels (I/O): {self.max_input_channels}/{self.max_output_channels}',
            f'\tDefault samplerate: {self.default_samplerate}',
            f'\tDefault interactive latency{self._format_latency(self.default_low_input_latency, self.default_low_output_latency)}',
            f'\tDefault non-interactive latency{self._format_latency(self.default_high_input_latency, self.default_low_output_latency)}'
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
        self._stopper = None

    @property
    def channels(self) -> int:
        return self.info.max_input_channels

    def log(self, msg: typing.Any) -> None:
        print(msg, sys.stderr)

    def destroy(self) -> None:
        if self._stopper is not None:
            self._stopper.set()


class SinkDevice(Device):
    # FIXME this should support buffer caching, right?
    input = slot('input')

    @property
    def type(self) -> SignalType:
        return SignalType.PLAYBACK

    def play(self):
        position = 0

        def callback(outdata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
            nonlocal position
            if status:
                self.log(status)
            shape = Shape(channels=self.channels, frames=frames)
            block = self.input.request(BlockLoc(position=position, shape=shape))
            outdata[:] = block
            position += frames

        self._stopper = threading.Event()

        with sd.OutputStream(device=self.info.index,
                             callback=callback,
                             finished_callback=self._stopper.set):
            self._stopper.wait()

    def _eval(self, request: Request):
        # FIXME refactor Signal hierarchy so that devices do not have to inherit
        # all the stuff in the current base class
        assert False, self


class SourceDevice(Device):

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self.q = queue.Queue()

    @property
    def type(self) -> SignalType:
        return SignalType.GENERATOR

    def _callback(self, indata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            self.log(status)
        if frames:
            # FIXME why is copy necessary?
            self.q.put(indata.copy())
        else:
            raise sd.CallbackStop

    def _start(self) -> None:

        self._stopper = threading.Event()
        with sd.InputStream(device=self.info.index,
                            callback=self._callback,
                            finished_callback=self._stopper.set):
            self._stopper.wait()

    def _eval(self, request: Request) -> np.ndarray:
        result = np.empty(request.loc.shape)
        block = self.q.get()

        return result
