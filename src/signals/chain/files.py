import functools
import pathlib
import abc
import tempfile

import soundfile as sf

import numpy as np

from signals.chain import (
    Event,
    SigState,
    Signal,
    BlockCachingSignal,
    SignalType,
    Request,
    Vis,
)


class SoundFileBase(Signal, abc.ABC):

    def __init__(self):
        super().__init__()
        self._buffer = None

    @property
    @abc.abstractmethod
    def _sample_path(self) -> pathlib.Path:
        raise NotImplementedError

    def _open(self, mode: str, position: int = 0) -> None:
        if self._buffer is None:
            self._buffer = sf.SoundFile(file=self._sample_path, mode=mode)
            self._open(mode, position)
        elif self._buffer.mode != mode:
            self._close()
            self._open(mode, position)
        else:
            assert self._buffer.mode == mode, self._buffer
            sought_postion = self._buffer.seek(position)
            assert position == sought_postion, (position, sought_postion)

    def _close(self) -> None:
        self._buffer.close()
        self._buffer = None

    def destroy(self) -> None:
        super().destroy()
        self._close()


class SoundFileReader(SoundFileBase, abc.ABC):

    def _read(self, request: Request) -> np.ndarray:
        self._open('r', request.loc.position)
        shape = request.loc.shape
        return self._buffer.read(frames=shape.frames)


class SoundFileWriter(SoundFileBase, abc.ABC):

    def _write(self, request: Request, block: np.ndarray) -> None:
        self._open('w', request.loc.position)
        self._buffer.write(block)


class BufferCachingSignal(SoundFileReader, SoundFileWriter, BlockCachingSignal, abc.ABC):

    def __init__(self):
        super().__init__()
        self.recording = False

    @functools.cached_property
    def _sample_path(self) -> pathlib.Path:
        return pathlib.Path(tempfile.mktemp(prefix='.'.join([
            'signals',
            'buffer_cache',
            type(self).__name__,
            id(self)
        ])))

    def _get_result(self, request: Request) -> np.ndarray:
        if self.recording:
            result = super()._get_result(request)
            self._write(request, result)
        else:
            result = self._read(request)
        return result


class SamplePlayer(SoundFileReader, BlockCachingSignal, Vis, Event):

    def __init__(self):
        super().__init__()
        self.path = None

    @property
    def type(self) -> SignalType:
        return SignalType.GENERATOR

    @property
    def _sample_path(self) -> pathlib.Path:
        return self.path

    @property
    def channels(self) -> int:
        return self._buffer.channels

    def _eval(self, request: Request) -> np.ndarray:
        return self._read(request)

    def get_state(self) -> SigState:
        return dict(
            super().get_state(),
            path=self.path
        )
