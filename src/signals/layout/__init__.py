import itertools
import math
import typing

import attr
import numpy as np

edge_width = 1 / 4

V = typing.TypeVar('V')


@attr.s(auto_attribs=True,
        frozen=False,
        kw_only=True,
        eq=False,
        hash=False)
class Vertex(typing.Generic[V]):
    inputs: list[typing.Self] = attr.ib(factory=list)
    outputs: list[typing.Self] = attr.ib(factory=list)
    x: typing.Optional[int] = attr.ib(default=None)
    y: typing.Optional[int] = attr.ib(default=None)
    w: float = attr.ib(default=1)
    value: V = attr.ib(default=None)

    __hash__ = object.__hash__
    __eq__ = object.__eq__

    @property
    def max_x(self) -> int:
        return self.x + math.ceil(self.w) - 1

    @property
    def is_placed(self) -> bool:
        return self.x is not None and self.y is not None

    neighbor_attr = typing.Literal['outputs', 'inputs']

    def replace_neighbor(self,
                         attr: neighbor_attr,
                         old: typing.Self,
                         new: typing.Self
                         ) -> None:
        neighbors = getattr(self, attr)
        index = neighbors.index(old)
        if index < 0:
            raise LookupError
        neighbors[index] = new

    def bridge_input(self, input: typing.Self) -> typing.Self:
        bridge = Vertex(inputs=[input], outputs=[self], w=edge_width)
        self.replace_neighbor('inputs', input, bridge)
        input.replace_neighbor('outputs', self, bridge)
        return bridge


class Subgraph(set[Vertex[V]]):
    """
    An improper subset of a graph.
    Vertices in the subgraph may be connected to inputs or outputs outside the
    subgraph.
    """

    def components(self) -> list[typing.Self]:
        """
        List connected components, ignoring edges that cross the subgraph
        boundary.
        """
        components = []
        for vertex in self:
            component = self & {vertex, *vertex.inputs, *vertex.outputs}
            for i in reversed(range(len(components))):
                if not component.isdisjoint(components[i]):
                    component |= components.pop(i)
            components.append(component)
        return components

    def strata(self) -> list[typing.Self]:
        """
        Partition a subgraph into its layers.
        A layer consists of all the vertices in the subgraph that have the same
        local depth. The local depth of a vertex is the length of the longest path
        to that vertex from a vertex with no inputs in the subgraph.
        """
        vertices = self.copy()
        strata = []
        while vertices:
            stratum = Subgraph(
                vertex
                for vertex in vertices
                if vertices.isdisjoint(vertex.inputs)
            )
            assert stratum, 'Cycle detected'
            vertices -= stratum
            strata.append(stratum)
        return strata

    @classmethod
    def bridge(cls, strata: list[typing.Self]) -> None:
        """
        Insert new vertices into the subgraphs, mutating existing vertices'
        connections so that every edge runs from layer `n` to layer `n+1`.
        """
        for outputs, inputs in itertools.pairwise(reversed(strata)):
            inputs.update(
                output.bridge_input(input)
                for output in outputs
                for input in output.inputs
                if input not in inputs
            )

    def untangle(self, neighbor_attr: Vertex.neighbor_attr) -> None:
        for vertex in self:
            # FIXME consider fixed port order?
            xs = [neighbor.x for neighbor in getattr(vertex, neighbor_attr)]
            vertex.x = sum(xs) // len(xs) if xs else np.inf
        # FIXME improve alignment
        i = 0
        for vertex in sorted(self, key=lambda n: n.x):
            vertex.x = i
            # FIXME allow multiple edges to run through the same grid cell
            i += math.ceil(vertex.w)

    @classmethod
    def untangle_strata(cls, strata: list[typing.Self], max_passes: int = 10) -> None:
        """
        Populate x-coordinates to try and minimize crossings of edges leading
        either to outputs or from inputs based on neighbor x-coordinates.
        Output is not guaranteed to be optimal due to NP-completeness.
        """
        xs = None
        for _ in range(max_passes):
            old_xs = xs
            for stratum in strata:
                stratum.untangle('inputs')
            for stratum in reversed(strata):
                stratum.untangle('outputs')
            xs = {vertex: vertex.x for stratum in strata for vertex in stratum}
            if xs == old_xs:
                break

    def layout(self) -> None:

        strata = self.strata()
        self.bridge(strata)
        self.untangle_strata(strata)
        for y, stratum in enumerate(strata):
            self.update(stratum)
            for vertex in stratum:
                vertex.y = y

        assert all(vertex.is_placed for vertex in self)
