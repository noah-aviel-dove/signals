import abc

import numpy as np

from signals import SignalFlags
from signals.chain import (
    BlockCachingEmitter,
    PassThroughShape,
    Receiver,
    Request,
    port,
)


class Effect(BlockCachingEmitter, PassThroughShape, abc.ABC):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.EFFECT


class UnaryEffect(Effect, abc.ABC):
    input: Receiver.BoundPort = port('input')


class BinaryEffect(Effect, abc.ABC):
    left: Receiver.BoundPort = port('left')
    right: Receiver.BoundPort = port('right')


class Add(BinaryEffect):

    def _eval(self, request: Request) -> np.ndarray:
        return self.left.forward(request) + self.right.forward(request)


class Mix(BinaryEffect):
    mix: Receiver.BoundPort = port('mix')

    def _eval(self, request: Request) -> np.ndarray:
        mix = self.mix.forward(request)
        return mix * self.left.forward(request) + (1 - mix) * self.right.forward(request)


class Gain(BinaryEffect):

    def _eval(self, request: Request) -> np.ndarray:
        return self.left.forward(request) * self.right.forward(request)
