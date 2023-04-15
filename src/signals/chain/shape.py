import abc

import attr
import attrs.validators
import numpy as np

from signals import SignalFlags
from signals.chain import (
    BlockCachingEmitter,
    Receiver,
    Request,
    port,
    state,
)


class Shaper(BlockCachingEmitter, Receiver, abc.ABC):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.EFFECT


class Scalar(Shaper, abc.ABC):
    input: Receiver.BoundPort = port('input')

    @property
    def channels(self) -> int:
        return 1


class Flatten(Scalar):

    def _eval(self, request: Request) -> np.ndarray:
        return np.sum(self.input.forward(request), axis=0)


class FlattenUnit(Scalar):

    def _eval(self, request: Request) -> np.ndarray:
        return np.mean(self.input.forward(request), axis=0)


class Select(Scalar):
    @state
    class State(BlockCachingEmitter.State):
        index: int = attr.ib(validator=attrs.validators.ge(0), default=0)

    def _get_result(self, request: Request) -> np.ndarray:
        channels = self.input.channels
        if channels is not None and self.state.index < channels:
            return super()._get_result(request)
        else:
            return self.empty_result()

    def _eval(self, request: Request) -> np.ndarray:
        return self.input.forward(request)[:, self.state.index]


class Merge(Shaper):

    @property
    def channels(self) -> int:
        return sum(input_.channels for input_ in self.inputs_by_port.values())

    left: Receiver.BoundPort = port('left')
    right: Receiver.BoundPort = port('right')

    def _eval(self, request: Request) -> np.ndarray:
        return np.hstack((self.left.forward(request), self.right.forward(request)))
