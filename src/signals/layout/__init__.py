import itertools
import math
import typing

import attr
import numpy as np

edge_width = 1 / 4


@attr.s(auto_attribs=True,
        frozen=False,
        kw_only=True,
        eq=False,
        hash=False,
        )
class Node:
    sources: list[typing.Self]
    sinks: list[typing.Self]
    x: typing.Optional[int] = attr.ib(default=None)
    y: typing.Optional[int] = attr.ib(default=None)
    w: float
    value: typing.Any = attr.ib(default=None)

    __hash__ = object.__hash__
    __eq__ = object.__eq__

    @property
    def max_x(self) -> int:
        return self.x + math.ceil(self.w) - 1

    @property
    def is_placed(self) -> bool:
        return self.x is not None and self.y is not None

    neighbor_attr = typing.Literal['sinks', 'sources']

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

    def bridge_source(self, source: typing.Self) -> typing.Self:
        bridge = Node(sources=[source], sinks=[self], w=edge_width)
        self.replace_neighbor('sources', source, bridge)
        source.replace_neighbor('sinks', self, bridge)
        return bridge


class Subgraph(set[Node]):
    """
    An improper subset of a graph.
    Nodes in the subgraph may be connected to sources or sinks outside the
    subgraph.
    """

    def components(self) -> list[typing.Self]:
        """
        List connected components, ignoring edges that cross the subgraph
        boundary.
        """
        components = []
        for node in self:
            component = self & {node, *node.sources, *node.sinks}
            for i in reversed(range(len(components))):
                if not component.isdisjoint(components[i]):
                    component |= components.pop(i)
            components.append(component)
        return components

    def strata(self) -> list[typing.Self]:
        """
        Partition a subgraph into its layers.
        A layer consists of all the nodes in the subgraph that have the same
        local depth. The local depth of a node is the length of the longest path
        to that node from a node with no sources in the subgraph.
        """
        nodes = self.copy()
        strata = []
        while nodes:
            stratum = Subgraph(
                node
                for node in nodes
                if nodes.isdisjoint(node.sources)
            )
            assert stratum, 'Cycle detected'
            nodes -= stratum
            strata.append(stratum)
        return strata

    @classmethod
    def bridge(cls, strata: list[typing.Self]) -> None:
        """
        Insert new nodes into the subgraphs, mutating existing nodes'
        connections so that every edge runs from layer `n` to layer `n+1`.
        """
        for sinks, sources in itertools.pairwise(reversed(strata)):
            sources.update(
                sink.bridge_source(source)
                for sink in sinks
                for source in sink.sources
                if source not in sources
            )

    def untangle(self, neighbor_attr: Node.neighbor_attr) -> None:
        for node in self:
            # FIXME consider fixed slot order?
            xs = [neighbor.x for neighbor in getattr(node, neighbor_attr)]
            node.x = sum(xs) // len(xs) if xs else np.inf
        # FIXME improve alignment
        i = 0
        for node in sorted(self, key=lambda n: n.x):
            node.x = i
            # FIXME allow multiple edges to run through the same grid cell
            i += math.ceil(node.w)

    @classmethod
    def untangle_strata(cls, strata: list[typing.Self], max_passes: int = 10) -> None:
        """
        Populate x-coordinates to try and minimize crossings of edges leading
        either to sinks or from sources based on neighbor x-coordinates.
        Output is not guaranteed to be optimal due to NP-completeness.
        """
        xs = None
        for _ in range(max_passes):
            old_xs = xs
            for stratum in strata:
                stratum.untangle('sources')
            for stratum in reversed(strata):
                stratum.untangle('sinks')
            xs = {node: node.x for stratum in strata for node in stratum}
            if xs == old_xs:
                break

    def do_layout(self) -> None:

        strata = self.strata()
        self.bridge(strata)
        self.untangle_strata(strata)
        for y, stratum in enumerate(strata):
            self.update(stratum)
            for node in stratum:
                node.y = y

        assert all(node.is_placed for node in self)
