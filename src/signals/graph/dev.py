import abc
import operator
import queue
import sys
import threading
import typing

import attr as attr
import numpy as np
import sounddevice as sd

from signals.graph import (
    BlockLoc,
    NodeType,
    Shape,
)
from signals.graph import (
    Node,
    Request,
    slot,
)


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
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


class Device(Node, abc.ABC):

    def __init__(self, info: DeviceInfo):
        super().__init__()
        self.info = info
        self._stopper = None

    @classmethod
    def list(cls) -> list[typing.Self]:
        return [
            cls(DeviceInfo(**info))
            for info in sorted(sd.query_devices(), key=operator.itemgetter('index'))
        ]

    @property
    def channels(self) -> int:
        return self.info.max_input_channels

    def log(self, msg: typing.Any) -> None:
        print(msg, sys.stderr)

    def destroy(self) -> None:
        self._stopper.set()


class SinkDevice(Device):
    input = slot('input')

    @property
    def type(self) -> NodeType:
        return NodeType.PLAYBACK

    @classmethod
    def list(cls) -> list[typing.Self]:
        return [dev for dev in super().list() if dev.info.max_output_channels > 0]

    def play(self):
        position = 0

        def callback(outdata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
            nonlocal position
            if status:
                self.log(status)
            shape = Shape(channels=self.channels, frames=frames)
            block = self.request(self.input, BlockLoc(position=position, shape=shape))
            outdata[:] = block
            position += frames

        self._stopper = threading.Event()

        with sd.OutputStream(device=self.info.index,
                             callback=callback,
                             finished_callback=self._stopper.set):
            self._stopper.wait()

    def _eval(self, request: Request):
        assert False, self


class SourceDevice(Device):

    def __init__(self, info: DeviceInfo):
        super().__init__(info)
        self.q = queue.Queue()

    @property
    def type(self) -> NodeType:
        return NodeType.GENERATOR

    @classmethod
    def list(cls) -> list[typing.Self]:
        return [dev for dev in super().list() if dev.info.max_input_channels > 0]

    def _callback(self, indata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            self.log(status)
        if frames:
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
