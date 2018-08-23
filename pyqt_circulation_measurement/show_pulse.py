import matplotlib.pyplot as plt
import os
from nmr_pulses import pulse_interpreter

BASE_FOLDER = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
pulse_file = 'simple_sequence.txt'
samp_rate = 1000000
pulse_data = pulse_interpreter(BASE_FOLDER +
                                '\pyqt_circulation_measurement\pulse_sequences\\' +
                                pulse_file, samp_rate,
                                 1)
plt.plot(pulse_data)
plt.show()
