from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import (
        FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import matplotlib

import sys
import os

import numpy as np
from numpy import pi

import json

import time

from nidaqmx.task import Task
from nidaqmx import constants


from nmr_pulses import pulse_interpreter

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

PARAMETER_FILE = BASE_FOLDER + r'\pyqt_circulation_measurement\parameter.txt'
'''
################################################################################
useful functions
'''

def read_parameter(parameter_file):
    with open(parameter_file, 'r') as f:
        parameter_raw = f.read()
    parameters = json.loads(parameter_raw)
    return parameters

def save_parameter(parameter_file, **kwargs):
    parameters = read_parameter(parameter_file)
    with open(parameter_file,'w') as f:
        for key,val in kwargs.items():
            parameters[key] = val
        json.dump(parameters, f, indent = 2)

'''
customized widget
'''
class MyLineEdit(QLineEdit):
    '''
    edit class for capturing input
    '''
    textModified = pyqtSignal(str,str) # (key, text)
    def __init__(self, key, contents='', parent=None):
        super(MyLineEdit, self).__init__(contents, parent)
        self.key = key
        self.editingFinished.connect(self.checkText)
        self.textChanged.connect(lambda: self.checkText())
        self.returnPressed.connect(lambda: self.checkText(True))
        self._before = contents

    def checkText(self, _return=False):
        if (not self.hasFocus() or _return):
            self._before = self.text()
            self.textModified.emit(self.key, self.text())

'''
################################################################################
Multithreading
'''



class WorkerSignals(QObject):
    data_measured = pyqtSignal(np.ndarray)
    data = pyqtSignal(tuple)


'''
-------------------------- read data--------------------------------------------
'''

class ReadDataWorker(QRunnable): #Multithreading
    def __init__(self, ao_task, ai_task, stop_btn, parameter, samp_num):
        super(ReadDataWorker,self).__init__()
        self.ao_task = ao_task
        self.ai_task = ai_task
        self.stop_btn = stop_btn
        self.average = int(parameter['average'])
        self.iteration = int(parameter['iteration'])
        self.samp_num = samp_num
        self.signals = WorkerSignals()


    @pyqtSlot()
    def run(self):
        for current_iter in range(self.iteration):
            '''
            initiate data in the current interation
            '''
            sig_data = np.zeros((3,self.samp_num))
            for current_avg in range(self.average):

                self.ai_task.start()
                self.ao_task.start()
                self.ai_task.wait_until_done()
                self.ao_task.wait_until_done()
                sig_data = (current_avg*sig_data + np.array(self.ai_task.read(number_of_samples_per_channel = self.samp_num)))/(current_avg+1)
                self.signals.data_measured.emit(sig_data)
                self.ai_task.stop()
                self.ao_task.stop()


class FourierWorker(QRunnable): #Multithreading
    def __init__(self, time_data_y, f_max, key):
        super(FourierWorker,self).__init__()
        self.f_max = f_max
        self.time_data_y = time_data_y
        self.signals = WorkerSignals()
        self.key = key
    @pyqtSlot()
    def run(self):
        self.freq_data_y = np.fft.rfft(self.time_data_y)/len(self.time_data_y)*2
        self.freq_data_x = np.linspace(0, self.f_max, int(len(self.time_data_y)/2)+1)
        self.signals.data.emit((self.freq_data_x,self.freq_data_y, self.key))




'''
################################################################################
main gui window intitation
'''

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow,self).__init__()

        self.parameters = read_parameter(PARAMETER_FILE)

        self.setWindowTitle('Circulation Measurement (NSOR project)')
        self.setWindowIcon(QIcon(BASE_FOLDER + r'\icons\window_icon.png'))

        '''
        --------------------------setting menubar-------------------------------
        '''
        mainMenu = self.menuBar() #create a menuBar
        fileMenu = mainMenu.addMenu('&File') #add a submenu to the menu bar

        '''
        --------------------------setting toolbar-------------------------------
        '''
        self.toolbar = self.addToolBar('nsor_toolbar') #add a tool bar to the window
        self.toolbar.setIconSize(QSize(100,100))

        self.statusBar() #create a status bar


        '''
        --------------------------setting matplotlib----------------------------
        axes are contained in one dictionary
        ax['nmr_time']
        ax['nmr_freq']
        ax['nsor_time']
        ax['nsor_freq']
        also initiate the vertical lines
        vline['time_l']
        vline['time_r']
        vline['freq_l']
        vline['freq_r']
        '''


        if app.desktop().screenGeometry().height() == 2160:
            matplotlib.rcParams.update({'font.size': 28})
        elif app.desktop().screenGeometry().height() == 1080:
            matplotlib.rcParams.update({'font.size': 14})
        canvas = FigureCanvas(Figure(figsize=(50, 15)))

        self.ax = {}
        self.vline = {}
        self.ax['nmr_time'] = canvas.figure.add_subplot(221)
        self.ax['nmr_freq'] = canvas.figure.add_subplot(222)
        self.ax['nsor_time'] = canvas.figure.add_subplot(223)
        self.ax['nsor_freq'] = canvas.figure.add_subplot(224)

        for axis in self.ax.values():
            if app.desktop().screenGeometry().height() == 2160:
                axis.tick_params(pad=20)
            elif app.desktop().screenGeometry().height() == 1080:
                axis.tick_params(pad=10)

        '''
        --------------------------setting widgets-------------------------------
        '''
        exitProgram = QAction(QIcon(BASE_FOLDER + r'\icons\exit_program.png'),'&Exit',self)
        exitProgram.setShortcut("Ctrl+W")
        exitProgram.setStatusTip('Close the Program')
        exitProgram.triggered.connect(self.exit_program)
        fileMenu.addAction(exitProgram)

        editParameters = QAction('&Edit Parameter', self)
        editParameters.setShortcut('Ctrl+E')
        editParameters.setStatusTip('open and edit the parameter file')
        editParameters.triggered.connect(lambda : os.startfile(PARAMETER_FILE))

        saveParameters = QAction('&Save Parameter', self)
        saveParameters.setShortcut('Ctrl+S')
        saveParameters.setStatusTip('save the parameters on screen to file')
        saveParameters.triggered.connect(self.save_parameters)

        editPulse = QAction('&Edit Pulse', self)
        editPulse.setShortcut('Ctrl+P')
        editPulse.setStatusTip('open and edit the pulse file')
        editPulse.triggered.connect(lambda : os.startfile(BASE_FOLDER +
                                        '\pyqt_circulation_measurement\pulse_sequences\\' +
                                        self.parameters['pulse_file']))

        parameterMenu = mainMenu.addMenu('&Parameter')
        parameterMenu.addAction(editParameters)
        parameterMenu.addAction(saveParameters)
        parameterMenu.addAction(editPulse)

        pulseHelp = QAction('&Pulse Example', self)
        pulseHelp.setStatusTip('check the example pulse file')
        pulseHelp.triggered.connect(lambda : os.startfile(BASE_FOLDER + r'\pyqt_circulation_measurement\pulse_sequences\model_sequence.txt'))

        helpMenu = mainMenu.addMenu('&Help')
        helpMenu.addAction(pulseHelp)



        startExpBtn = QPushButton('START',self)
        startExpBtn.clicked.connect(self.start_experiment)
        self.stopBtn = QPushButton('STOP',self)
        self.stopBtn.setCheckable(True)
        updateParamBtn = QPushButton('Update Parameter', self)
        updateParamBtn.clicked.connect(self.update_parameter)

        '''
        --------------------------setting layout/mix widget set-----------------
        '''
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.North)
        tabs.setMovable(True)

        tab = {'parameter': QWidget(), 'data': QWidget()}
        tab_layout = {'parameter' : QVBoxLayout(), 'data': QHBoxLayout()}
        parameter_tab_layout = QFormLayout()
        sub_tab_layout = {'time': QVBoxLayout(), 'freq':QVBoxLayout()}
        '''
        importing edits from paramter
        '''
        self.edits = {}

        for key,value in self.parameters.items():
            if type(value) == list:
                value = str(value[0])+' '+str(value[1])
            self.edits[key] = MyLineEdit(key, value, self)
            self.edits[key].setStatusTip(f'{key}')
            if 'nmr' in key:
                key_str = 'NMR Channel'
            elif 'nsor' in key:
                key_str = 'NSOR Channel'
            else:
                key_str = key.replace('_', ' ').title()

            if not ('time' in key or 'freq' in key):
                '''
                parameter tab layout:
                file_name; pulse_file; samp_rate; iteration; average; pulse_chan;
                nmr_chan; nsor_chan; laser_chan
                also add the signals to them
                '''
                self.edits[key].textModified.connect(self.parameter_change)

                layout_temp = QHBoxLayout()
                layout_temp.addWidget(self.edits[key])
                if 'file_name' in key:
                    self.edits[key].setFixedWidth(1250)
                else:
                    layout_temp.addStretch(1)

                parameter_tab_layout.addRow(key_str,layout_temp)

            else:
                '''
                data tab layout:
                time_x_limit; time_y_limit; freq_x_limit; freq_y_limit;
                time_cursor; freq_cursor
                also add the signals
                '''
                self.edits[key].textModified.connect(self.limit_and_cursor)

                sub_tab_layout[key[0:4]].addWidget(QLabel(key_str,self))
                sub_tab_layout[key[0:4]].addWidget(self.edits[key])
                if 'freq' in key:
                    self.edits[key].setFixedWidth(250)



        for key in sub_tab_layout.keys():
            sub_tab_layout[key].addStretch(1)

        tab_layout['parameter'].addLayout(parameter_tab_layout)
        tab_layout['parameter'].addWidget(updateParamBtn)
        tab_layout['parameter'].addStretch(1)
        button_layout = QHBoxLayout()
        button_layout.addWidget(startExpBtn)
        button_layout.addWidget(self.stopBtn)
        button_layout.addStretch(1)
        tab_layout['parameter'].addLayout(button_layout)

        tab_layout['data'].addLayout(sub_tab_layout['time'])
        tab_layout['data'].addWidget(canvas)
        tab_layout['data'].addLayout(sub_tab_layout['freq'])
        for key in tab.keys():
            tabs.addTab(tab[key], key)
            tab[key].setLayout(tab_layout[key])


        _main = QWidget()
        self.setCentralWidget(_main)
        layout1 = QVBoxLayout(_main)
        layout1.addWidget(tabs)


        '''
        --------------------------Multithreading preparation--------------------
        '''
        self.threadpool = QThreadPool() #Multithreading


        '''
        --------------------------Daqmx Task initialization---------------------
        '''
        self.sig_task = Task('signal_task')
        self.pulse_task = Task('pulse task')
        self.update_parameter()


        '''
        -------------------------Menu bar slot----------------------------------
        '''
    # def edit_parameters(self):
    #     os.startfile(PARAMETER_FILE)

    def save_parameters(self):
        for key in self.parameters.keys():
            str = self.edits[key].text()
            if 'freq' in key or 'time' in key:
                self.parameters[key] = str.split(' ')
            else:
                self.parameters[key] = str

        save_parameter(PARAMETER_FILE, **self.parameters)

    def exit_program(self):
        choice = QMessageBox.question(self, 'Exiting',
                                                'Are you sure about exit?',
                                                QMessageBox.Yes | QMessageBox.No) #Set a QMessageBox when called
        if choice == QMessageBox.Yes:  # give actions when answered the question
            sys.exit()

    '''
    --------------------------parameter update slots----------------------------
    '''
    def limit_and_cursor(self, key, text):
        pass

    def parameter_change(self, key, text):
        self.parameters[key] = text

    def update_parameter(self):
        self.sig_task.close()
        self.pulse_task.close()
        samp_rate = int(self.parameters['sampling_rate'])
        pulse_data = pulse_interpreter(BASE_FOLDER +
                                        '\pyqt_circulation_measurement\pulse_sequences\\' +
                                        self.parameters['pulse_file'], samp_rate,
                                         int(self.parameters['iteration']))
        self.samp_num = len(pulse_data)
        self.sig_task = Task('signal_task')
        self.pulse_task = Task('pulse task')
        for key,item in self.parameters.items():
            if 'channel' in key:
                if 'pulse' in key:
                    self.pulse_task.ao_channels.add_ao_voltage_chan(item)
                else:
                    self.sig_task.ai_channels.add_ai_voltage_chan(physical_channel = item,
                            terminal_config = constants.TerminalConfiguration.DIFFERENTIAL)

        self.pulse_task.timing.cfg_samp_clk_timing(rate = samp_rate,
                        samps_per_chan = self.samp_num,
                        sample_mode=constants.AcquisitionType.FINITE)
        self.sig_task.timing.cfg_samp_clk_timing(rate = samp_rate,
                     source = '/Dev1/ao/SampleClock',
                     samps_per_chan = self.samp_num,
                     sample_mode=constants.AcquisitionType.FINITE)
        self.pulse_task.write(pulse_data)
        self.time_data = np.linspace(0,(self.samp_num/samp_rate), self.samp_num)
        self.time_data = np.reshape(self.time_data,(1,self.samp_num))

    '''
    --------------------------Multithreading slots------------------------------
    '''
    def start_experiment(self):
        worker = ReadDataWorker(self.pulse_task, self.sig_task, self.stopBtn, self.parameters, self.samp_num)
        worker.signals.data_measured.connect(self.store_plot_data)
        self.threadpool.start(worker)

    def store_plot_data(self, data):
        if self.stopBtn.isChecked():
            self.stopBtn.toggle()
        np.save(self.parameters['file_name'], np.concatenate((self.time_data, data)))
        self.ax['nmr_time'].clear()
        self.ax['nmr_time'].plot(self.time_data[0,:], data[0,:])
        self.ax['nsor_time'].clear()
        self.ax['nsor_time'].plot(self.time_data[0,:], data[1,:])

        f_max = int(self.parameters['sampling_rate'])/2
        fourier_worker_nmr = FourierWorker(data[0,:], f_max, 'nmr_freq')
        fourier_worker_nmr.signals.data.connect(self.set_fourier)
        self.threadpool.start(fourier_worker_nmr)

        fourier_worker_nsor = FourierWorker(data[1,:], f_max, 'nsor_freq')
        fourier_worker_nsor.signals.data.connect(self.set_fourier)
        self.threadpool.start(fourier_worker_nsor)

    def set_fourier(self, data):
        key = data[2]
        self.ax[key].clear()
        self.ax[key].plot(data[0], np.abs(data[1]))

'''
################################################################################
'''

app = QApplication(sys.argv)

window = MainWindow()
window.move(300,300)
window.show()
app.exec_()
