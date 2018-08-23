from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib

import numpy as np

import sys
import os
import ntpath

from nmr_pulses import pulse_interpreter

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


'''
################################################################################
main gui window intitation
'''

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow,self).__init__()

        self.setWindowTitle('Pulse Visualizer')
        self.setWindowIcon(QIcon(BASE_FOLDER + r'\pyqt_analysis\icons\window_icon.png'))

        '''
        --------------------------setting menubar-------------------------------
        '''
        mainMenu = self.menuBar() #create a menuBar
        fileMenu = mainMenu.addMenu('&File') #add a submenu to the menu bar


        self.statusBar() #create a status bar

        '''
        --------------------------setting matplotlib----------------------------
        '''
        if app.desktop().screenGeometry().height() == 2160:
            matplotlib.rcParams.update({'font.size': 28})
        elif app.desktop().screenGeometry().height() == 1080:
            matplotlib.rcParams.update({'font.size': 14})


        self.canvas = FigureCanvas(Figure(figsize=(25, 15)))
        self.addToolBar(NavigationToolbar(self.canvas, self))


        self.ax = self.canvas.figure.add_subplot(111)
        if app.desktop().screenGeometry().height() == 2160:
            self.ax.tick_params(pad=20)
        elif app.desktop().screenGeometry().height() == 1080:
            self.ax.tick_params(pad=10)

        '''
        --------------------------setting widgets-------------------------------
        '''
        openFile = QAction(QIcon(r'C:\Users\yue\ownCloud\Yue\python\pyqt_analysis\icons\open_file.png'),'&Open File...',self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open the data file')
        openFile.triggered.connect(self.open_file)
        fileMenu.addAction(openFile)

        exitProgram = QAction(QIcon(BASE_FOLDER + r'\pyqt_analysis\icons\exit_program.png'),'&Exit',self)
        exitProgram.setShortcut("Ctrl+W")
        exitProgram.setStatusTip('Close the Program')
        exitProgram.triggered.connect(self.exit_program)
        fileMenu.addAction(exitProgram)

        self.file_name = 'simple_sequence.txt'
        self.file_name_label = QLabel(self.file_name)

        redraw_pulse = QPushButton('REDRAW',self)
        redraw_pulse.clicked.connect(self.redraw)


        editPulse = QAction('&Edit Pulse', self)
        editPulse.setShortcut('Ctrl+P')
        editPulse.setStatusTip('open and edit the pulse file')
        self.file_path = BASE_FOLDER + '\pyqt_circulation_measurement\pulse_sequences\\' + self.file_name
        editPulse.triggered.connect(lambda : os.startfile(self.file_path))

        pulseMenu = mainMenu.addMenu('&Pulse')
        pulseMenu.addAction(editPulse)


        '''
        --------------------------setting layout--------------------------------
        '''

        _main = QWidget()
        self.setCentralWidget(_main)
        layout1 = QVBoxLayout(_main)

        layout2 = QHBoxLayout()
        layout2.addWidget(redraw_pulse)
        layout2.addStretch(1)

        layout1.addWidget(self.canvas)
        layout1.addWidget(self.file_name_label)
        layout1.addLayout(layout2)

    def exit_program(self):
        choice = QMessageBox.question(self, 'Exiting',
                                                'Are you sure about exit?',
                                                QMessageBox.Yes | QMessageBox.No) #Set a QMessageBox when called
        if choice == QMessageBox.Yes:  # give actions when answered the question
            sys.exit()

    def open_file(self):
        '''
        open file and plot the pulse
        '''

        dlg = QFileDialog()
        dlg.setDirectory(BASE_FOLDER)
        if dlg.exec_():
            self.file_path = dlg.selectedFiles()[0]

        self.file_name = ntpath.basename(self.file_path)
        self.file_name_label.setText(self.file_name)

        self.redraw()

    def redraw(self):
        '''
        redraw the pulse specified with self.file_path
        '''
        samp_rate = 1000000
        pulse_data = pulse_interpreter(self.file_path, samp_rate, 1)
        time_data = np.linspace(0,len(pulse_data)/samp_rate,len(pulse_data))

        self.ax.clear()
        self.ax.plot(time_data,pulse_data)
        self.canvas.draw()

'''
################################################################################
'''

app = QApplication(sys.argv)

window = MainWindow()
window.move(300,300)
window.show()
app.exec_()
