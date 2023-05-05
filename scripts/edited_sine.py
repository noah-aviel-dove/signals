import time

import numpy as np

import signals.chain.dev
import signals.chain.discovery
import signals.chain.fixed
import signals.chain.osc
import signals.map.control


def main():
    rack = signals.chain.discovery.Rack()
    rack.scan()
    for sink in rack.sinks():
        print(sink)

    choice = input('Enter device name: ')
    sink = signals.chain.dev.SinkDevice(rack.get_sink(choice))

    sine = signals.chain.osc.Sine()
    sink.input = sine

    phase = signals.chain.fixed.Fixed()
    sine.phase = phase

    sine_hertz = signals.chain.fixed.Fixed()
    sine_hertz.value = np.array([440], ndmin=2)
    sine.hertz = sine_hertz

    sink.start()
    while sink.is_active:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            sink.destroy()
            break


if __name__ == '__main__':
    main()
