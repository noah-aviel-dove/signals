import pathlib

import numpy as np

from signals.graph.node import (
    BlockCachingNode,
    Request,
    SoundFileReader,
)


class SamplePlayer(SoundFileReader, BlockCachingNode):

    def __init__(self):
        super().__init__()
        self._path = None

    @property
    def _sample_path(self) -> pathlib.Path:
        return self._path

    @property
    def channels(self) -> int:
        return self._buffer.channels

    def _eval(self, request: Request) -> np.ndarray:
        return self._read(request)
