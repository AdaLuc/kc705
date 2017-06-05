
from ctypes import windll
windll.shcore.SetProcessDpiAwareness(True)

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PyQt5 import QtGui, QtCore, QtWidgets, uic, Qt
import os, sys
from cgi import escape
import threading

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation


#import pydaq as daq
import daq2 as daq

from qtthreadutils import invoke_in_main_thread
import numpy as np

form_class = uic.loadUiType("runcontrol.ui")[0]

class MainWindow(QtWidgets.QMainWindow, form_class):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        # keep this object alive by saving a reference
        self.events = MyEventListener(self)
        self.dataTaker = daq.DataTaker(self.events)

        # scale factor for high dpi screens
        sf = self.logicalDpiX() / 96
        self.setupStyle(sf)

        self.dpi = 100 * sf
        self.fig = Figure((3.0, 4.0), dpi=self.dpi)
        self.fig.patch.set_visible(False)

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.graph)
        size = self.fig.get_size_inches()*self.fig.dpi
        self.graph.setMinimumSize(*size)

        self.axes = self.fig.add_subplot(111)

        zeros = np.zeros(shape=(48,16))
        self.image = self.axes.imshow(zeros, animated=True, interpolation='nearest')
        self.canvas.show()

        self.mpl_toolbar = NavigationToolbar(self.canvas, self.graph)

        self.btnStartRun.clicked.connect(self.btnStartRun_clicked)
        self.btnStopRun.clicked.connect(self.btnStopRun_clicked)

        self.timer = Qt.QTimer()
        self.timer.timeout.connect(self.update_state)
        self.timer.start(1000)

        # logging
        self.textEdit.document().setDefaultStyleSheet("""
        .error {color: red}
        .warning {color: orange}
        .debug {color: grey}
        .info {color: black}
        """)
        self.textEdit.setReadOnly(True)
        self.textEdit.setUndoRedoEnabled(False)

        self.update_state()



    def setupStyle(self, sf):
        self.setStyleSheet("""
            QToolButton {
                padding: """+str(int(6*sf))+"""px;
                border-radius: """+str(int(2*sf))+"""px;
                border: 1px solid transparent;
            }
            QToolButton::hover {
                background-color: rgba(0, 120, 215, 0.1);
                border: 1px solid #0078D7;
            }        

            QGroupBox {
                /*border: """+str(int(2*sf))+"""px groove #ADADAD;*/
                border: """+str(int(1*sf))+"""px solid #C0C0C0;
                border-radius: """+str(int(4*sf))+"""px;
                margin-top: 0.70em;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: """+str(int(7*sf))+"""px;
                padding: 0 """+str(int(3*sf))+"""px 0 """+str(int(3*sf))+"""px;
            }

/*            QMenuBar {
                border-bottom: """+str(int(2*sf))+"""px groove #ADADAD;
                padding: """+str(int(2*sf))+"""px;
            }*/
        """)

    def btnStartRun_clicked(self, arg):
        self.dataTaker.start_run()
        self.update_state()

    def btnStopRun_clicked(self, arg):
        self.dataTaker.stop_run()
        self.update_state()

    def logMessage(self, level, thread_name, string):
        print(string)

        prev_cursor = self.textEdit.textCursor()
        self.textEdit.moveCursor(Qt.QTextCursor.End)

        #self.textEdit.insertPlainText(thread_name + "\t" + string + "\n")
        message = escape(string, True) + "\n"
        classNames = {
            daq.LOG_DEBUG: 'debug',
            daq.LOG_INFO: 'info',
            daq.LOG_WARNING: 'warning',
            daq.LOG_ERROR: 'error',
        }
        className = classNames[level]
        self.textEdit.insertPlainText(thread_name + "\t")
        self.textEdit.insertHtml('<div class="%s">%s</div><br>' % (className, message))
        self.textEdit.setTextCursor(prev_cursor)

    def update_state(self):
        print ("In update_state")
        state = self.dataTaker.get_state()
        self.lblState.setText(str(state))
        self.statusBar().showMessage(str(state))
        self.btnStartRun.setEnabled(state == daq.STATE_STOPPED)
        self.btnStopRun.setEnabled(state == daq.STATE_RUNNING)
        nevents = self.dataTaker.get_event_number()
        self.lblEventNumber.setText(str(nevents))
        runNumber = self.dataTaker.get_run_number()
        self.lblRunNumber.setText(str(runNumber))

        # print ("here")

        if state == daq.STATE_STOPPED:
            if self.timer.isActive():
                self.timer.stop()

        elif state == daq.STATE_RUNNING:
            if not self.timer.isActive():
                self.timer.start()

        # last_events = self.dataTaker.get_accumulated_events()
        last_events = None
        if last_events:
            summed = sum(last_events)
            self.image.set_data(summed)
            self.image.autoscale()

            self.axes.draw_artist(self.image)
            self.canvas.update()


class MyEventListener(daq.EventListener):
    def __init__(self, window):
        super().__init__()
        self._window = window

    def logMessage(self, level, string):
        print("In logMessage")
        thread = threading.current_thread()
        # invoke_in_main_thread(self._window.logMessage, level, thread.name, string)
        invoke_in_main_thread(self._window.logMessage, level, thread.name, string)


def main():
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()

    win.show()
    # really quit even if we have running threads
    # this does not e.g. write buffered files to disk,
    # I'm using it for testing only:
    os._exit(app.exec_())
    # sys.exit(app.exec_())


if __name__ == '__main__':
    main()