import abc

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
