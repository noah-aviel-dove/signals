import abc
import typing

import attr
import numpy as np

from signals.chain import (
    BlockCachingSignal,
    PassThroughShape,
    Request,
    SignalType,
    Vis,
    port,
)


class Osc(BlockCachingSignal, PassThroughShape, Vis, abc.ABC):
    sclock = port('sclock')
    hertz = port('hertz')
    phase = port('phase')

    @property
    def type(self) -> SignalType:
        return SignalType.GENERATOR

    def _eval(self, request: Request) -> np.ndarray:
        t = self.sclock.forward(request)
        phase = self.phase.forward_at_block_rate(request)
        hertz = self.hertz.forward_at_block_rate(request)
        return self._osc(phase + hertz * t)

    @abc.abstractmethod
    def _osc(self, t: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class Sine(Osc):

    def _osc(self, t: np.ndarray) -> np.ndarray:
        return np.sin(t * 2 * np.pi)


class Square(Osc):

    def _osc(self, t: np.ndarray) -> np.ndarray:
        return np.sign(0.5 - np.mod(t, 1))


class Sawtooth(Osc):

    def _osc(self, t: np.ndarray) -> np.ndarray:
        return 2 * np.mod(t - 0.5, 1) - 1


class Triangle(Osc):

    def _osc(self, t: np.ndarray) -> np.ndarray:
        t = t - 0.25
        return (4 * np.mod(t, 0.5) - 1) * np.sign(np.mod(t, 1) - 0.5)


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
