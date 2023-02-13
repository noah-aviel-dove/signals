import numpy as np

from signals.chain import (
    SignalType,
    Shape,
)
from signals.chain import (
    Signal,
    Request,
)


class Fixed(Signal):

    def __init__(self):
        super().__init__()
        self.value = np.zeros((1, 1))

    @property
    def type(self) -> SignalType:
        return SignalType.VALUE

    @property
    def channels(self) -> int:
        return Shape.of_array(self.value).channels

    def _eval(self, request: Request) -> np.ndarray:
        return self.value
