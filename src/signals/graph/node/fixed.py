import numpy as np

from signals.graph import (
    Shape,
)
from signals.graph.node import (
    Node,
    Request,
)


class Fixed(Node):

    def __init__(self):
        super().__init__()
        self.value = np.zeros((1, 1))

    @property
    def channels(self) -> int:
        return Shape.of_array(self.value).channels

    def _eval(self, request: Request) -> np.ndarray:
        return self.value
