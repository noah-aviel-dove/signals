import abc
import queue

import attr
import matplotlib.pyplot as plt
import numpy as np

from signals import (
    SignalFlags,
)
from signals.chain import (
    PassThroughResult,
    Request,
    Shape,
    state,
)


class Vis(PassThroughResult, abc.ABC):

    def __init__(self):
        super().__init__()
        self.q = queue.Queue()

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags() | SignalFlags.VIS

    def render(self, ax: plt.Axes, frames: int) -> list[plt.Artist]:
        blocks = []
        queued_frames = 0
        while True:
            try:
                block = self.q.get_nowait()
            except queue.Empty:
                break
            else:
                # FIXME take part of a block to fill frames completely
                queued_frames += Shape.of_array(block).frames
                if queued_frames <= frames:
                    blocks.append(block)
                else:
                    # Blocks that exceed the frame limit are dropped
                    pass

        ax.clear()
        result = []
        if blocks:
            x = 0
            for block in blocks[:-1]:
                x += Shape.of_array(block).frames
                result.append(ax.axvline(x, c='black'))
            result.extend(self._plot(np.concatenate(blocks), ax))
        ax.set_xlim(0, frames)
        return result

    @abc.abstractmethod
    def _plot(self, block: np.ndarray, ax: plt.Axes) -> list[plt.Artist]:
        raise NotImplementedError

    def _eval(self, request: Request) -> np.ndarray:
        result = self.input.forward(request)
        self.q.put(result)
        return result


class Wave(Vis):
    @state
    class State(Vis.State):
        min_amp: float = attr.ib(default=-1.)
        max_amp: float = attr.ib(default=+1.)

    def _plot(self, block: np.ndarray, ax: plt.Axes) -> list[plt.Artist]:
        ax.set_ylim(self._state.min_amp, self._state.max_amp)
        return ax.plot(block)


class Spec(Vis):
    @state
    class State(Vis.State):
        min_freq: float = attr.ib(default=0)
        max_freq: float = attr.ib(default=22000)
        bands: int = attr.ib(default=80)

    def _plot(self, block: np.ndarray, ax: plt.Axes) -> None:
        ax.set_ylim(self._state.min_freq, self._state.max_freq)
        # sketch, this obviously does not work
        data = np.fft.rfft(block)
        return ax.bar(data)
