import abc

import numpy as np

from signals.chain import (
    BlockCachingSignal,
    Request,
    SignalType,
    slot,
)


class Clock(BlockCachingSignal, abc.ABC):

    @property
    def channels(self) -> int:
        return 1

    def type(self) -> SignalType:
        return SignalType.GENERATOR


class TimeClock(Clock):

    hertz = slot('hertz')

    def _eval(self, request: Request) -> np.ndarray:
        hertz = self.hertz.forward(request)
        return (np.arange(request.loc.position, request.loc.end_position) / hertz).reshape(-1, 1)


class TempoClock(Clock):
    tclock = slot('tclock')
    bpm = slot('bpm')

    def _eval(self, request: Request) -> np.ndarray:
        t = self.tclock.forward(request)
        bpm = self.bpm.forward(request)
        return t * bpm / 60
