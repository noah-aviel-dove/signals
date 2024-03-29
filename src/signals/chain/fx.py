import abc
import enum
import typing

import numpy as np
import scipy.signal

from signals import (
    SignalFlags,
)
from signals.chain import (
    BlockCachingEmitter,
    ImplicitChannels,
    Receiver,
    Request,
    Shape,
    port,
)


# FIXME many of these should use PassThroughResult

class Effect(BlockCachingEmitter, ImplicitChannels, abc.ABC):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.EFFECT


class BinaryEffect(Effect, abc.ABC):
    left: Receiver.BoundPort = port('left')
    right: Receiver.BoundPort = port('right')


class Mix(BinaryEffect):
    mix: Receiver.BoundPort = port('mix')

    def _eval(self, request: Request) -> np.ndarray:
        mix = self.mix.forward_at_block_rate(request)
        return mix * self.left.forward(request) + (1 - mix) * self.right.forward(request)


class RingMod(BinaryEffect):

    def _eval(self, request: Request) -> np.ndarray:
        return self.left.forward(request) * self.right.forward(request)


class Gain(BinaryEffect):

    def _eval(self, request: Request) -> np.ndarray:
        return self.left.forward(request) * self.right.forward_at_block_rate(request)


class Amp(BinaryEffect):

    def _eval(self, request: Request) -> np.ndarray:
        input_ = self.left.forward(request)
        exp = self.right.forward_at_block_rate(request)
        return np.copysign(input_ ** exp, input_)


class CritFilter(Effect, abc.ABC):
    input: Receiver.BoundPort = port('input')

    order = 2

    class Type(enum.StrEnum):
        low_pass = 'lp'
        high_pass = 'hp'
        band_pass = 'bp'
        band_stop = 'bs'

        @property
        def is_band(self) -> bool:
            return self.startswith('b')

    @abc.abstractmethod
    def type(self) -> Type:
        raise NotImplementedError

    def context_frames(self) -> int:
        return 100

    def _filter(self,
                request: Request,
                crit_1: np.ndarray,
                crit_2: np.ndarray | None = None
                ) -> np.ndarray:
        assert Shape.of_array(crit_1).frames == 1
        if crit_2 is not None:
            assert Shape.of_array(crit_2).frames == 1
        context_frames = self.context_frames()
        input_ = self.input.forward_with_context(request, context_frames)
        shape = request.loc.shape
        result = np.empty(shape=shape)
        rate = request.loc.rate
        for i in range(shape.channels):
            scaled_crit = np.array((crit_1[0, i], *(() if crit_2 is None else crit_2[0, i])), dtype=np.float)
            scaled_crit /= rate / 2
            scaled_crit.clip(0, 1, out=scaled_crit)
            sos = self._get_sos(self.type(), self.order, scaled_crit, rate)
            input_slice = slice(-(shape.frames + context_frames), -context_frames)
            assert (input_slice.stop - input_slice.start) == shape.frames
            result[:, i] = scipy.signal.sosfilt(sos, input_[:, i], axis=0)[input_slice]
        return result

    def _get_sos(self,
                 type_: Type,
                 order: int,
                 scaled_crit: typing.Sequence[float],
                 rate: float
                 ):
        # Not caching this because the output must be mutable for `sosfilt`
        return scipy.signal.butter(
            N=order,
            Wn=scaled_crit,
            #fs=rate,
            btype=type_,
            output='sos'
        )


class SingleCritFilter(CritFilter, abc.ABC):
    cutoff: Receiver.BoundPort = port('cutoff')

    def _eval(self, request: Request) -> np.ndarray:
        hertz = self.cutoff.forward_at_block_rate(request)
        return self._filter(request, hertz)


class DoubleCritFilter(CritFilter, abc.ABC):
    low: Receiver.BoundPort = port('low')
    high: Receiver.BoundPort = port('high')

    def _eval(self, request: Request) -> np.ndarray:
        low = self.low.forward_at_block_rate(request)
        high = self.high.forward_at_block_rate(request)
        return self._filter(request, low, high)


class LowPass(SingleCritFilter):

    def type(self) -> CritFilter.Type:
        return self.Type.low_pass


class HighPass(SingleCritFilter):

    def type(self) -> CritFilter.Type:
        return self.Type.high_pass


class BandPass(DoubleCritFilter):

    def type(self) -> CritFilter.Type:
        return self.Type.band_pass


class BandStop(DoubleCritFilter):

    def type(self) -> CritFilter.Type:
        return self.Type.band_stop
