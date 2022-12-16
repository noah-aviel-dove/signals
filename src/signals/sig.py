import abc
import enum
import pathlib
import sys
import typing

import more_itertools
import numpy as np
import sounddevice as sd
import soundfile as sf


class Control:
    pass


class Sig(abc.ABC):

    def __init__(self):
        self.sample_rate = Control()
        self.frame = 0
        self.enabled = True
        self.audio_rate = True

    @abc.abstractmethod
    @property
    def channels(self) -> int:
        raise NotImplementedError

    def _apply(self, outdata: np.ndarray) -> None:
        raise NotImplementedError

    def __call__(self, outdata: np.ndarray, frames: int, time: typing.Any, status: sd.CallbackFlags) -> None:
        if status:
            print(status, sys.stderr)
        assert outdata.shape == (frames, self.channels), (outdata.shape, frames, self.channels)
        self._apply(outdata)
        self.frame += frames

    def _frames(self, frames: int) -> np.ndarray:
        return np.arange(self.frame, self.frame + (frames if self.audio_rate else 0))


class Gen(Sig, abc.ABC):

    @abc.abstractmethod
    def _alloc(self, frames: int) -> np.ndarray:
        raise NotImplementedError

    def _apply(self, outdata: np.ndarray) -> None:
        outdata[:] = self._alloc(outdata.shape[1])


class Const(Gen):

    def __init__(self, val):
        super().__init__()
        self.val = val

    @property
    def channels(self) -> int:
        return 1

    def _alloc(self, frames: int) -> np.ndarray:
        return np.array([self.val])


class Period(Gen):

    def __init__(self):
        super().__init__()
        self.start = Const(0)
        self.stop = Const(1)

    def channels(self) -> int:
        return 1

    def _alloc(self, frames: int) -> np.ndarray:
        return (self.start <= self._frames(frames) <= self.stop).astype(float)


class Curve(Gen, abc.ABC):

    @property
    def channels(self) -> int:
        return 1


class Segment(Period, Curve):

    def __init__(self):
        super().__init__()
        self.start_val = Const(0)
        self.stop_val = Const(0)
        self.exp = Const(1)

    def _alloc(self, frames: int) -> np.ndarray:
        mask = super()._alloc(frames)
        curve = (((self._frames(frames) - self.start) / (self.stop - self.start))**self.exp + self.start_val) * self.stop_val
        return curve * mask


class Osc(Curve):
    class OscType(enum.Enum):
        sine = np.sin

    def __init__(self):
        super().__init__()
        self.freq = Control()
        self.osc_type = self.OscEnum.sine

    def _alloc(self, frames: int) -> np.ndarray:
        freq = self.freq * 2 * np.pi / self.sample_rate
        return self.osc_type.value(freq * self._frames(frames)).reshape(-1, 1)


class Samp(Gen):

    def __init__(self, path: pathlib.Path):
        super().__init__()
        self.data, sr = sf.read(str(path), always_2d=False)
        assert sr == self.sample_rate, (sr, self.sample_rate)

    @property
    def channels(self) -> int:
        return self.data.shape[1]

    def _alloc(self, frames: int) -> np.ndarray:
        return np.tile(self.data, np.ceil(frames / len(self.data)).astype(int))[:frames]


class Gain(Sig):

    def __init__(self):
        super().__init__()
        self.amp = Const(1)

    @property
    def channels(self) -> int:
        return self.amp.channels

    def _apply(self, outdata: np.ndarray) -> None:
        outdata *= self.amp


class Offset(Sig):

    def channels(self) -> int:
        return more_itertools.one({c.channels for c in self.inputs})

    def __init__(self):
        super().__init__()
        self.offset = Const(0)

    def _apply(self, outdata: np.ndarrayt) -> None:
        outdata += self.offset
