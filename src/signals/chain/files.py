import abc
import functools
import pathlib
import tempfile

import attr
import numpy as np
import soundfile as sf

from signals import (
    SignalFlags,
)
from signals.chain import (
    BlockCachingEmitter,
    PassThroughShape,
    Request,
    Signal,
    port,
    state,
)


class SoundFileBase(Signal, abc.ABC):

    def __init__(self):
        super().__init__()
        self._buffer = None

    @property
    @abc.abstractmethod
    def _file_path(self) -> pathlib.Path:
        raise NotImplementedError

    def _open(self, mode: str, position: int = 0) -> None:
        if self._buffer is None:
            self._buffer = sf.SoundFile(file=self._file_path, mode=mode)
            self._open(mode, position)
        elif self._buffer.mode != mode:
            self._close()
            self._open(mode, position)
        else:
            assert self._buffer.mode == mode, self._buffer
            sought_position = self._buffer.seek(position)
            assert position == sought_position, (position, sought_position)

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


class RecordingEmitter(SoundFileReader, SoundFileWriter, BlockCachingEmitter, abc.ABC):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.RECORDER

    @functools.cached_property
    def _file_path(self) -> pathlib.Path:
        return pathlib.Path(tempfile.mktemp(prefix='.'.join([
            'signals',
            'buffer_cache',
            type(self).__name__,
            id(self)
        ])))


# FIXME test performance with and without block cache
class Recorder(RecordingEmitter, PassThroughShape):

    input = port('input')

    def __init__(self):
        super().__init__()
        self.recording = False

    def _eval(self, request: Request) -> np.ndarray:
        return self.input.forward(request)

    def _get_result(self, request: Request) -> np.ndarray:
        if self.recording:
            result = super()._get_result(request)
            self._write(request, result)
        else:
            result = self._read(request)
        return result


# FIXME test performance with and without block cache
class SamplePlayer(SoundFileReader, BlockCachingEmitter):
    @state
    class State(BlockCachingEmitter.State):
        path: pathlib.Path = attr.ib(default='', converter=pathlib.Path)

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.GENERATOR

    @property
    def _file_path(self) -> pathlib.Path:
        return self._state.path

    @property
    def channels(self) -> int:
        return self._buffer.channels

    def _eval(self, request: Request) -> np.ndarray:
        return self._read(request)
