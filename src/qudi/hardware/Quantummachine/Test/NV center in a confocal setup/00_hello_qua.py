"""
        HELLO QUA
A simple sandbox to showcase different QUA functionalities during the installation.
"""

import time
from qm import SimulationConfig, LoopbackInterface
from qm.qua import *
from qm.QuantumMachinesManager import QuantumMachinesManager
from configuration import *
import matplotlib.pyplot as plt

###################
# The QUA program #
###################
readout_len = long_meas_len_1

with program() as hello_QUA:
    a = declare(fixed)
    with infinite_loop_():
        play("cw" * amp(1), "NV", duration=readout_len * u.ns)
        '''
        with for_(a, 0, a < 1.1, a + 0.05):
            play("x180" * amp(a), "NV")
        '''
        #align()
        #play("x180" * amp(1), "NV")
        #play("laser_ON", "AOM1", duration=readout_len * u.ns)
        #wait(100, "NV")

#####################################
#  Open Communication with the QOP  #
#####################################
qmm = QuantumMachinesManager(qop_ip, cluster_name=cluster_name)

###########################
# Run or Simulate Program #
###########################

simulate = False

if simulate:
    # Simulates the QUA program for the specified duration
    simulation_config = SimulationConfig(duration=3_000)  # In clock cycles = 4ns
    job_sim = qmm.simulate(config, hello_QUA, simulation_config)
    # Simulate blocks python until the simulation is done
    job_sim.get_simulated_samples().con1.plot()
    plt.show()

else:
    qm = qmm.open_qm(config)
    job = qm.execute(hello_QUA)
    # Execute does not block python! As this is an infinite loop, the job would run forever. In this case, we've put a 10
    # seconds sleep and then halted the job.
    time.sleep(10)
    job.halt()