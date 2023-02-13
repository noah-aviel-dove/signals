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

    @property
    def type(self) -> SignalType:
        return SignalType.GENERATOR


class TimeClock(Clock):

    hertz = slot('hertz')

    def _eval(self, request: Request) -> np.ndarray:
        hertz = self.forward_request(self.hertz, request)
        return (np.arange(request.loc.position, request.loc.stop) / hertz).reshape(-1, 1)


class TempoClock(Clock):
    tclock = slot('tclock')
    bpm = slot('bpm')

    def _eval(self, request: Request) -> np.ndarray:
        t = self.forward_request(self.tclock, request)
        bpm = self.forward_request(self.bpm, request)
        return t * bpm / 60
