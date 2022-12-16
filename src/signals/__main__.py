import more_itertools
import numpy as np

import signals.graph.node.clock
import signals.graph.node.dev
import signals.graph.node.fixed
import signals.graph.node.osc


def main():
    sinks = signals.graph.node.dev.SinkDevice.list()
    sink = more_itertools.one(sink for sink in sinks if sink.info.name == 'default')

    sine = signals.graph.node.osc.Sine()
    sink.input = sine

    phase = signals.graph.node.fixed.Fixed()
    sine.phase = phase

    sine_hertz = signals.graph.node.fixed.Fixed()
    sine_hertz.value = np.array([440], ndmin=2)
    sine.hertz = sine_hertz

    sample_rate = signals.graph.node.fixed.Fixed()
    sample_rate.value = np.array([sink.info.default_samplerate], ndmin=2)

    clock = signals.graph.node.clock.TimeClock()
    clock.hertz = sample_rate

    sine.sclock = clock

    sink.play()


if __name__ == '__main__':
    main()
