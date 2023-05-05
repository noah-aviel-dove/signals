import abc

import numpy as np

from signals import SignalFlags
from signals.chain import (
    BlockCachingEmitter,
    ExplicitChannelsEmitter,
    Request,
)


class Noise(ExplicitChannelsEmitter, BlockCachingEmitter, abc.ABC):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.GENERATOR


class White(Noise):

    def _eval(self, request: Request) -> np.ndarray:
        return np.random.rand(*request.loc.shape)
