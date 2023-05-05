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
    Emitter,
    PassThroughResult,
    Request,
    Signal,
    state,
)


class SoundFileBase(Emitter, abc.ABC):

    def __init__(self):
        super().__init__()
        self._buffer: sf.SoundFile | None = None

    @state
    class State(Emitter.State):

        @staticmethod
        def _validate_file_path(*args) -> None:
            pass

        path: str = attr.ib(default='/dev/null', validator=_validate_file_path)

    @property
    def _file_path(self) -> pathlib.Path:
        return pathlib.Path(self._state.path)

    def _open(self, mode: str, request: Request) -> None:
        if self._buffer is None:
            self._buffer = sf.SoundFile(file=self._file_path,
                                        mode=mode,
                                        samplerate=request.loc.rate,
                                        channels=request.loc.shape.channels)
            self._open(mode, request)
        # FIXME fix handling of mismatch between request.channels and file.channels
        elif self._buffer.mode != mode or self._buffer.samplerate != request.loc.rate:
            self._close()
            self._open(mode, request)
        else:
            assert self._buffer.mode == mode, self._buffer
            assert self._buffer.samplerate == request.loc.rate, self._buffer
            position = request.loc.position
            sought_position = self._buffer.seek(position)
            assert position == sought_position, (position, sought_position)

    def _close(self) -> None:
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None

    def destroy(self) -> None:
        self._close()
        super().destroy()


class FileReader(SoundFileBase):

    def _read(self, request: Request) -> np.ndarray:
        self._open('r', request)
        shape = request.loc.shape
        return self._buffer.read(frames=shape.frames, always_2d=True)

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.GENERATOR

    @property
    def channels(self) -> int:
        return self._buffer.channels

    def _eval(self, request: Request) -> np.ndarray:
        return self._read(request)


class FileWriter(SoundFileBase, PassThroughResult):

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.RECORDER

    def _write(self, request: Request, block: np.ndarray) -> None:
        self._open('w', request)
        self._buffer.write(block)

    def _eval(self, request: Request) -> np.ndarray:
        result = self.input.forward(request)
        self._write(request, result)
        return result
