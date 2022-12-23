import more_itertools
import numpy as np

import signals.graph.clock
import signals.graph.dev
import signals.graph.fixed
import signals.graph.osc


def main():
    sinks = signals.graph.dev.SinkDevice.list()
    for sink in sinks:
        print(sink.info.index, sink.info.name)
    choice = int(input('? '))
    sink = more_itertools.one(sink for sink in sinks if sink.info.index == choice)

    sine = signals.graph.osc.Sine()
    sink.input = sine

    phase = signals.graph.fixed.Fixed()
    sine.phase = phase

    sine_hertz = signals.graph.fixed.Fixed()
    sine_hertz.value = np.array([440], ndmin=2)
    sine.hertz = sine_hertz

    sample_rate = signals.graph.fixed.Fixed()
    sample_rate.value = np.array([sink.info.default_samplerate], ndmin=2)

    clock = signals.graph.clock.TimeClock()
    clock.hertz = sample_rate

    sine.sclock = clock

    sink.play()


if __name__ == '__main__':
    main()
