import numpy as np

from signals import (
    SignalFlags,
)
from signals.chain import (
    Emitter,
    Request,
    Shape,
)


class Fixed(Emitter):

    def __init__(self):
        super().__init__()
        self.value = np.zeros((1, 1))

    @classmethod
    def flags(cls) -> SignalFlags:
        return super().flags()

    @property
    def channels(self) -> int:
        return Shape.of_array(self.value).channels

    def _eval(self, request: Request) -> np.ndarray:
        return self.value

    def get_state(self) -> dict:
        assert self.value.ndim == 2, self.value
        state = super().get_state()
        state['value'] = self.value.tolist()
        return state
