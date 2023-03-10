import sys
import faulthandler

import signals.ui.window

if __name__ == '__main__':
    faulthandler.enable()
    app = signals.App(sys.argv)
    window = signals.ui.window.MainWindow()
    window.show()
    sys.exit(app.exec_())
