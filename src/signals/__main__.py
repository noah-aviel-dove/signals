import sys

import signals.graph.dev
import signals.ui.window


if __name__ == '__main__':
    app = signals.App(sys.argv)
    window = signals.ui.window.MainWindow()
    window.show()
    sys.exit(app.exec_())
