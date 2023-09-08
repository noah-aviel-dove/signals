import abc
import typing

import attr
import numpy as np

from signals import (
    SignalFlags,
)
from signals.chain import (
    BlockCachingEmitter,
    ImplicitChannels,
    Request,
    port,
)


class Osc(BlockCachingEmitter, ImplicitChannels, abc.ABC):
    hertz = port('hertz')
    phase = port('phase')

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.GENERATOR

    def _eval(self, request: Request) -> np.ndarray:
        # phase: cycles
        phase = self.phase.forward_at_block_rate(request)
        # hertz: cycles/second
        hertz = self.hertz.forward_at_block_rate(request)
        # frames / (frames / second) * (cycles / second) + cycles
        cycles = request.loc.frame_range / request.loc.rate
        cycles *= hertz
        cycles += phase
        self._osc(cycles)
        return cycles

    @abc.abstractmethod
    def _osc(self, t: np.ndarray) -> None:
        raise NotImplementedError


class Sine(Osc):

    def _osc(self, t: np.ndarray) -> None:
        t *= np.pi * 2
        np.sin(t, out=t)


class Square(Osc):

    def _osc(self, t: np.ndarray) -> None:
        np.mod(t, 1, out=t)
        np.subtract(0.5, t, out=t)
        np.sign(t, out=t)


class Sawtooth(Osc):

    def _osc(self, t: np.ndarray) -> None:
        t -= 0.5
        np.mod(t, 1, out=t)
        t *= 2
        t -= 1


class Triangle(Osc):

    def _osc(self, t: np.ndarray) -> None:
        np.subtract(0.25, t, out=t)
        t2 = np.mod(t, 1)
        t2 -= 0.5
        np.mod(t, 0.5, out=t)
        t *= 4
        t -= 1
        np.copysign(t, t2, out=t)


@attr.s(auto_attribs=True, frozen=True, kw_only=True)
class OscTable:
    # Testing indicates that this is actually significantly slower than just
    # calling the function across the entire request range
    framerate: int
    hertz: float
    buffer: np.ndarray

    @classmethod
    def create(cls,
               hertz: float,
               framerate: int,
               func: typing.Callable[[np.ndarray], np.ndarray]) -> typing.Self:
        # hertz: cycles/second
        # framerate: frames/second
        frames_per_cycle = int(framerate / hertz)
        buffer = func(np.arange(frames_per_cycle)/frames_per_cycle)
        assert len(buffer) == frames_per_cycle
        buffer.flags.writeable = False
        return cls(hertz=hertz,
                   framerate=framerate,
                   buffer=buffer)

    def read(self, phase: float, size: int) -> np.ndarray:
        # phase: cycles
        frames_per_cycle = len(self.buffer)
        phase = int(phase % 1.0 * frames_per_cycle) % frames_per_cycle
        # phase: frames
        if phase + size <= frames_per_cycle:
            result = self.buffer[phase:phase + size]
        elif phase + size <= frames_per_cycle * 2:
            result = np.concatenate((self.buffer[phase:],
                                     self.buffer[:(phase + size) % frames_per_cycle]))
        else:
            pad_before = frames_per_cycle - phase
            pad_after = (phase + size) - frames_per_cycle * 2
            result = np.pad(self.buffer, (pad_before, pad_after), mode='wrap')
        assert len(result) == size
        return result
