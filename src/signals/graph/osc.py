import abc

import numpy as np

from signals.graph import (
    BlockCachingNode,
    NodeType,
    PassThroughShape,
    Request,
    Shape,
    Vis,
    slot,
)


class Osc(BlockCachingNode, PassThroughShape, Vis, abc.ABC):
    sclock = slot('sclock')
    hertz = slot('hertz')
    phase = slot('phase')

    @property
    def type(self) -> NodeType:
        return NodeType.GENERATOR

    def _eval(self, request: Request) -> np.ndarray:
        t = self.forward_request(self.sclock, request)
        # I don't want to deal with making these vary at sample rate
        block = Shape(channels=self.channels, frames=1)
        phase = self.forward_request(self.phase, request, block)
        hertz = self.forward_request(self.hertz, request, block)
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
