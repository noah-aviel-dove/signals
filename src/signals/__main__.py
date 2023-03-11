import sys
import faulthandler

import signals.ui.patcher.window

if __name__ == '__main__':
    faulthandler.enable()
    app = signals.App(sys.argv)
    app.load(signals.Project.default())
    window = signals.ui.patcher.window.Window()
    window.show()
    sys.exit(app.exec_())
