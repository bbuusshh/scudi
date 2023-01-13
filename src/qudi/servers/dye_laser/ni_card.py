import numpy as np
import re
import time
import PyDAQmx as daq 

class NationalInstruments():
    _clock_channel =  '/Dev1/Ctr0'
    _counter_voltage_range = [-10, 10]
    default_scanner_clock_frequency = 100
    _default_clock_frequency = 1000
    _counter_channels = ['/Dev1/Ctr1']
    _counter_ai_channels = ['/Dev1/AI0']
    _scanner_clock_channel =  '/Dev1/Ctr2'
    _pixel_clock_channel =  '/Dev1/PFI6' 
    _scanner_ao_channels = ['/Dev1/AO0','/Dev1/AO1','/Dev1/AO2','/Dev1/AO3']
    
    _scanner_ai_channels = ['/Dev1/AI1']
    _scanner_counter_channels = ['/Dev1/Ctr3']
    _scanner_voltage_ranges = [[-10, 10], 
    [-5, 5], # stepper voltage
    [-10, 0], #thin etalon 
    [-10, 10]]
    _scanner_position_ranges = [[-10, 10], 
    [-5, 5], # stepper voltage
     [-10, 0], #thin etalon  
     [-10, 10]]
    _default_samples_number =  50
    _max_counts =  3e7
    _read_write_timeout =  10
    _counting_edge_rising =  True
    _photon_sources =  list()
    _stepper_pulse_channel =  'Dev1/port1/line4'
    _flip_mirror_channel = 'Dev1/port0/line1'
    _shutter_channel =  'Dev1/port0/line16'

    # timeout for the Read or/and write process in s
    _RWTimeout = 10

    def __init__(self):
        """ Starts up the NI Card at activation.
        """
        # the tasks used on that hardware device:
        self._counter_daq_tasks = list()
        self._counter_analog_daq_task = None
        self._clock_daq_task = None
        self._scanner_clock_daq_task = None
        self._scanner_ao_task = None
        self._scanner_counter_daq_tasks = list()
        self._line_length = None
        self._odmr_length = None
        self._gated_counter_daq_task = None
        self._scanner_analog_daq_task = None
        self._odmr_pulser_daq_task = None
        self._oversampling = 0
        self._lock_in_active = False

        self._photon_sources = self._photon_sources if self._photon_sources is not None else list()
        self._scanner_counter_channels = self._scanner_counter_channels if self._scanner_counter_channels is not None else list()
        self._scanner_ai_channels = self._scanner_ai_channels if self._scanner_ai_channels is not None else list()

        # handle all the parameters given by the config
        self._current_position = np.zeros(len(self._scanner_ao_channels))

        if len(self._scanner_ao_channels) < len(self._scanner_voltage_ranges):
            print(
                'Specify at least as many scanner_voltage_ranges as scanner_ao_channels!')

        if len(self._scanner_ao_channels) < len(self._scanner_position_ranges):
            print(
                'Specify at least as many scanner_position_ranges as scanner_ao_channels!')

        if len(self._scanner_counter_channels) + len(self._scanner_ai_channels) < 1:
            print(
                'Specify at least one counter or analog input channel for the scanner!')

        # Analog output is always needed and it does not interfere with the
        # rest, so start it always and leave it running
        if self._start_analog_output() < 0:
            print('Failed to start analog output.')
            raise Exception('Failed to start NI Card module due to analog output failure.')

    def on_deactivate(self):
        """ Shut down the NI card.
        """
        self._stop_analog_output()
        # clear the task
        try:
            daq.DAQmxClearTask(self._scanner_ao_task)
            self._scanner_ao_task = None
        except:
            self.log.exception('Could not clear AO Out Task.')

        self.reset_hardware()

    # =================== SlowCounterInterface Commands ========================

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 4
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def set_up_clock(self, clock_frequency=None, clock_channel=None, scanner=False, idle=False):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock in Hz
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock within the NI card.
        @param bool scanner: if set to True method will set up a clock function
                             for the scanner, otherwise a clock function for a
                             counter will be set.
        @param bool idle: set whether idle situation of the counter (where
                          counter is doing nothing) is defined as
                                True  = 'Voltage High/Rising Edge'
                                False = 'Voltage Low/Falling Edge'

        @return int: error code (0:OK, -1:error)
        """

        if not scanner and self._clock_daq_task is not None:
            print('Another counter clock is already running, close this one first.')
            return -1

        if scanner and self._scanner_clock_daq_task is not None:
            print('Another scanner clock is already running, close this one first.')
            return -1

        # Create handle for task, this task will generate pulse signal for
        # photon counting
        my_clock_daq_task = daq.TaskHandle()

        # assign the clock frequency, if given
        if clock_frequency is not None:
            if not scanner:
                self._clock_frequency = float(clock_frequency)
            else:
                self._scanner_clock_frequency = float(clock_frequency)
        else:
            if not scanner:
                self._clock_frequency = self._default_clock_frequency
            else:
                self._scanner_clock_frequency = self._default_scanner_clock_frequency

        # use the correct clock in this method
        if scanner:
            my_clock_frequency = self._scanner_clock_frequency * 2
        else:
            my_clock_frequency = self._clock_frequency * 2

        # assign the clock channel, if given
        if clock_channel is not None:
            if not scanner:
                self._clock_channel = clock_channel
            else:
                self._scanner_clock_channel = clock_channel

        # use the correct clock channel in this method
        if scanner:
            my_clock_channel = self._scanner_clock_channel
        else:
            my_clock_channel = self._clock_channel

        # check whether only one clock pair is available, since some NI cards
        # only one clock channel pair.
        if self._scanner_clock_channel == self._clock_channel:
            if not ((self._clock_daq_task is None) and (self._scanner_clock_daq_task is None)):
                print(
                    'Only one clock channel is available!\n'
                    'Another clock is already running, close this one first '
                    'in order to use it for your purpose!')
                return -1

        # Adjust the idle state if necessary
        my_idle = daq.DAQmx_Val_High if idle else daq.DAQmx_Val_Low
        try:
            # create task for clock
            task_name = 'ScannerClock' if scanner else 'CounterClock'
            daq.DAQmxCreateTask(task_name, daq.byref(my_clock_daq_task))

            # create a digital clock channel with specific clock frequency:
            daq.DAQmxCreateCOPulseChanFreq(
                # The task to which to add the channels
                my_clock_daq_task,
                # which channel is used?
                my_clock_channel,
                # Name to assign to task (NIDAQ uses by # default the physical channel name as
                # the virtual channel name. If name is specified, then you must use the name
                # when you refer to that channel in other NIDAQ functions)
                'Clock Producer',
                # units, Hertz in our case
                daq.DAQmx_Val_Hz,
                # idle state
                my_idle,
                # initial delay
                0,
                # pulse frequency, divide by 2 such that length of semi period = count_interval
                my_clock_frequency / 2,
                # duty cycle of pulses, 0.5 such that high and low duration are both
                # equal to count_interval
                0.5)

            # Configure Implicit Timing.
            # Set timing to continuous, i.e. set only the number of samples to
            # acquire or generate without specifying timing:
            daq.DAQmxCfgImplicitTiming(
                # Define task
                my_clock_daq_task,
                # Sample Mode: set the task to generate a continuous amount of running samples
                daq.DAQmx_Val_ContSamps,
                # buffer length which stores temporarily the number of generated samples
                1000)

            if scanner:
                self._scanner_clock_daq_task = my_clock_daq_task
            else:
                # actually start the preconfigured clock task
                daq.DAQmxStartTask(my_clock_daq_task)
                self._clock_daq_task = my_clock_daq_task
        except:
            self.log.exception('Error while setting up clock.')
            return -1
        return 0

    def set_up_counter(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       counter_buffer=None):
        """ Configures the actual counter with a given clock.

        @param list(str) counter_channels: optional, physical channel of the counter
        @param list(str) sources: optional, physical channel where the photons
                                  are to count from
        @param str clock_channel: optional, specifies the clock channel for the
                                  counter
        @param int counter_buffer: optional, a buffer of specified integer
                                   length, where in each bin the count numbers
                                   are saved.

        @return int: error code (0:OK, -1:error)
        """

        if self._clock_daq_task is None and clock_channel is None:
            print('No clock running, call set_up_clock before starting the counter.')
            return -1

        if len(self._counter_daq_tasks) > 0:
            print('Another counter is already running, close this one first.')
            return -1

        my_counter_channels = counter_channels if counter_channels else self._counter_channels
        my_photon_sources = sources if sources else self._photon_sources
        my_clock_channel = clock_channel if clock_channel else self._clock_channel

        if len(my_photon_sources) < len(my_counter_channels):
            print('You have given {0} sources but {1} counting channels.'
                           'Please give an equal or greater number of sources.'
                           ''.format(len(my_photon_sources), len(my_counter_channels)))
            return -1

        try:
            for i, ch in enumerate(my_counter_channels):
                # This task will count photons with binning defined by the clock_channel
                task = daq.TaskHandle()  # Initialize a Task
                # Create task for the counter
                daq.DAQmxCreateTask('Counter{0}'.format(i), daq.byref(task))
                # Create a Counter Input which samples with Semi-Periodes the Channel.
                # set up semi period width measurement in photon ticks, i.e. the width
                # of each pulse (high and low) generated by pulse_out_task is measured
                # in photon ticks.
                #   (this task creates a channel to measure the time between state
                #    transitions of a digital signal and adds the channel to the task
                #    you choose)
                daq.DAQmxCreateCISemiPeriodChan(
                    # define to which task to connect this function
                    task,
                    # use this counter channel
                    ch,
                    # name to assign to it
                    'Counter Channel {0}'.format(i),
                    # expected minimum count value
                    0,
                    # Expected maximum count value
                    self._max_counts / 2 / self._clock_frequency,
                    # units of width measurement, here photon ticks
                    daq.DAQmx_Val_Ticks,
                    # empty extra argument
                    '')

                # Set the Counter Input to a Semi Period input Terminal.
                # Connect the pulses from the counter clock to the counter channel
                daq.DAQmxSetCISemiPeriodTerm(
                        # The task to which to add the counter channel.
                        task,
                        # use this counter channel
                        ch,
                        # assign a named Terminal
                        my_clock_channel + 'InternalOutput')

                # Set a Counter Input Control Timebase Source.
                # Specify the terminal of the timebase which is used for the counter:
                # Define the source of ticks for the counter as self._photon_source for
                # the Scanner Task.
                daq.DAQmxSetCICtrTimebaseSrc(
                    # define to which task to connect this function
                    task,
                    # counter channel
                    ch,
                    # counter channel to output the counting results
                    my_photon_sources[i])

                # Configure Implicit Timing.
                # Set timing to continuous, i.e. set only the number of samples to
                # acquire or generate without specifying timing:
                daq.DAQmxCfgImplicitTiming(
                    # define to which task to connect this function
                    task,
                    # Sample Mode: Acquire or generate samples until you stop the task.
                    daq.DAQmx_Val_ContSamps,
                    # buffer length which stores  temporarily the number of generated samples
                    1000)

                # Set the Read point Relative To an operation.
                # Specifies the point in the buffer at which to begin a read operation.
                # Here we read most recent recorded samples:
                daq.DAQmxSetReadRelativeTo(
                    # define to which task to connect this function
                    task,
                    # Start reading samples relative to the last sample returned by the previously.
                    daq.DAQmx_Val_CurrReadPos)

                # Set the Read Offset.
                # Specifies an offset in samples per channel at which to begin a read
                # operation. This offset is relative to the location you specify with
                # RelativeTo. Here we set the Offset to 0 for multiple samples:
                daq.DAQmxSetReadOffset(task, 0)

                # Set Read OverWrite Mode.
                # Specifies whether to overwrite samples in the buffer that you have
                # not yet read. Unread data in buffer will be overwritten:
                daq.DAQmxSetReadOverWrite(
                    task,
                    daq.DAQmx_Val_DoNotOverwriteUnreadSamps)
                # add task to counter task list
                self._counter_daq_tasks.append(task)

                # Counter analog input task
                if len(self._counter_ai_channels) > 0:
                    atask = daq.TaskHandle()

                    daq.DAQmxCreateTask('CounterAnalogIn', daq.byref(atask))

                    daq.DAQmxCreateAIVoltageChan(
                        atask,
                        ', '.join(self._counter_ai_channels),
                        'Counter Analog In',
                        daq.DAQmx_Val_RSE,
                        self._counter_voltage_range[0],
                        self._counter_voltage_range[1],
                        daq.DAQmx_Val_Volts,
                        ''
                    )
                    # Analog in channel timebase
                    daq.DAQmxCfgSampClkTiming(
                        atask,
                        my_clock_channel + 'InternalOutput',
                        self._clock_frequency,
                        daq.DAQmx_Val_Rising,
                        daq.DAQmx_Val_ContSamps,
                        int(self._clock_frequency * 5)
                    )
                    self._counter_analog_daq_task = atask
        except:
            self.log.exception('Error while setting up counting task.')
            return -1

        try:
            for i, task in enumerate(self._counter_daq_tasks):
                # Actually start the preconfigured counter task
                daq.DAQmxStartTask(task)
            if len(self._counter_ai_channels) > 0:
                daq.DAQmxStartTask(self._counter_analog_daq_task)
        except:
            self.log.exception('Error while starting Counter')
            try:
                self.close_counter()
            except:
                self.log.exception('Could not close counter after error')
            return -1
        return 0

    def get_counter_channels(self):
        """ Returns the list of counter channel names.

        @return tuple(str): channel names

        Most methods calling this might just care about the number of channels, though.
        """
        ch = self._counter_channels[:]
        ch.extend(self._counter_ai_channels)
        return ch

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go.
                            How many samples are read per readout cycle. The
                            readout frequency was defined in the counter setup.
                            That sets also the length of the readout array.

        @return float [samples]: array with entries as photon counts per second
        """
        if len(self._counter_daq_tasks) < 1:
            print(
                'No counter running, call set_up_counter before reading it.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        if len(self._counter_ai_channels) > 0 and self._counter_analog_daq_task is None:
            print(
                'No counter analog input task running, call set_up_counter before reading it.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        if samples is None:
            samples = int(self._samples_number)
        else:
            samples = int(samples)
        try:
            # count data will be written here in the NumPy array of length samples
            count_data = np.empty((len(self._counter_daq_tasks), 2 * samples), dtype=np.uint32)

            # number of samples which were actually read, will be stored here
            n_read_samples = daq.int32()
            for i, task in enumerate(self._counter_daq_tasks):
                # read the counter value: This function is blocking and waits for the
                # counts to be all filled:
                daq.DAQmxReadCounterU32(
                    # read from this task
                    task,
                    # number of samples to read
                    2 * samples,
                    # maximal timeout for the read process
                    self._RWTimeout,
                    # write the readout into this array
                    count_data[i],
                    # length of array to write into
                    2 * samples,
                    # number of samples which were read
                    daq.byref(n_read_samples),
                    # Reserved for future use. Pass NULL (here None) to this parameter
                    None)

            # Analog channels
            if len(self._counter_ai_channels) > 0:
                analog_data = np.full(
                    (len(self._counter_ai_channels), samples), 111, dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._counter_analog_daq_task,
                    samples,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    analog_data,
                    len(self._counter_ai_channels) * samples,
                    daq.byref(analog_read_samples),
                    None
                )
        except:
            self.log.exception(
                'Getting samples from counter failed.')
            # in case of error return a lot of -1
            return np.ones((len(self.get_counter_channels()), samples), dtype=np.uint32) * -1

        real_data = np.empty((len(self._counter_channels), samples), dtype=np.uint32)

        # add up adjoint pixels to also get the counts from the low time of
        # the clock:
        real_data = count_data[:, ::2]
        real_data += count_data[:, 1::2]

        all_data = np.full((len(self.get_counter_channels()), samples), 222, dtype=np.float64)
        # normalize to counts per second for counter channels
        all_data[0:len(real_data)] = np.array(real_data * self._clock_frequency, np.float64)

        if len(self._counter_ai_channels) > 0:
            all_data[-len(self._counter_ai_channels):] = analog_data

        return all_data

    def close_counter(self, scanner=False):
        """ Closes the counter or scanner and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             will be excecuted to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        error = 0
        if scanner:
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                try:
                    # stop the counter task
                    daq.DAQmxStopTask(task)
                    # after stopping delete all the configuration of the counter
                    daq.DAQmxClearTask(task)
                except:
                    self.log.exception('Could not close scanner counter.')
                    error = -1
            self._scanner_counter_daq_tasks = []
        else:
            for i, task in enumerate(self._counter_daq_tasks):
                try:
                    # stop the counter task
                    daq.DAQmxStopTask(task)
                    # after stopping delete all the configuration of the counter
                    daq.DAQmxClearTask(task)
                    # set the task handle to None as a safety
                except:
                    self.log.exception('Could not close counter.')
                    error = -1
            self._counter_daq_tasks = []

            if len(self._counter_ai_channels) > 0:
                try:
                    # stop the counter task
                    daq.DAQmxStopTask(self._counter_analog_daq_task)
                    # after stopping delete all the configuration of the counter
                    daq.DAQmxClearTask(self._counter_analog_daq_task)
                    # set the task handle to None as a safety
                except:
                    self.log.exception('Could not close counter analog channels.')
                    error = -1
                self._counter_analog_daq_task = None
        return error

    def close_clock(self, scanner=False):
        """ Closes the clock and cleans up afterwards.

        @param bool scanner: specifies if the counter- or scanner- function
                             should be used to close the device.
                                True = scanner
                                False = counter

        @return int: error code (0:OK, -1:error)
        """
        if scanner:
            my_task = self._scanner_clock_daq_task
        else:
            my_task = self._clock_daq_task
        try:
            # Stop the clock task:
            daq.DAQmxStopTask(my_task)

            # After stopping delete all the configuration of the clock:
            daq.DAQmxClearTask(my_task)

            # Set the task handle to None as a safety
            if scanner:
                self._scanner_clock_daq_task = None
            else:
                self._clock_daq_task = None
        except:
            self.log.exception('Could not close clock.')
            return -1
        return 0

    # ================ End SlowCounterInterface Commands =======================

    # ================ ScannerInterface Commands =======================
    def reset_hardware(self):
        """ Resets the NI hardware, so the connection is lost and other
            programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        chanlist = [
            self._odmr_trigger_channel,
            self._clock_channel,
            self._scanner_clock_channel,
            self._gate_in_channel
            ]
        chanlist.extend(self._scanner_ao_channels)
        chanlist.extend(self._photon_sources)
        chanlist.extend(self._counter_channels)
        chanlist.extend(self._scanner_counter_channels)

        devicelist = []


    def get_scanner_axes(self):
        """ Scanner axes depends on how many channels tha analog output task has.
        """
        if self._scanner_ao_task is None:
            print('Cannot get channel number, analog output task does not exist.')
            return []

        n_channels = daq.uInt32()
        daq.DAQmxGetTaskNumChans(self._scanner_ao_task, n_channels)
        possible_channels = ['x', 'y', 'z', 'a']

        return possible_channels[0:int(n_channels.value)]

    def get_scanner_count_channels(self):
        """ Return list of counter channels """
        ch = self._scanner_counter_channels[:]
        ch.extend(self._scanner_ai_channels)
        return ch

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit. The unit of the scan range is
                              meters.
        """
        return self._scanner_position_ranges

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit. The unit of the
                                     scan range is meters.

        @return int: error code (0:OK, -1:error)
        """
        n_ch = len(self.get_scanner_axes())
        if myrange is None:
            myrange = [[0, 1e-6], [0, 1e-6], [0, 1e-6], [0, 1e-6]][0:n_ch]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray, )):
            print('Given range is no array type.')
            return -1

        if len(myrange) != 4:
            print(
                'Given range should have dimension 4, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for pos in myrange:
            if len(pos) != 2:
                print(
                    'Given range limit {1:d} should have dimension 2, but has {0:d} instead.'
                    ''.format(len(pos), pos))
                return -1
            if pos[0]>pos[1]:
                print(
                    'Given range limit {0:d} has the wrong order.'.format(pos))
                return -1

        self._scanner_position_ranges = myrange
        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [n][2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        n_ch = len(self.get_scanner_axes())
        if myrange is None:
            myrange = [[0., 10.], [0., 10.], [0., 10.], [0., 10.]][0:n_ch]

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray)):
            print('Given range is no array type.')
            return -1

        if len(myrange) != n_ch:
            print(
                'Given range should have dimension 2, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for r in myrange:
            if r[0] > r[1]:
                print('Given range limit {0:d} has the wrong order.'.format(r))
                return -1

        self._scanner_voltage_ranges = myrange
        return 0

    def _start_analog_output(self):
        """ Starts or restarts the analog output.

        @return int: error code (0:OK, -1:error)
        """
        try:
            # If an analog task is already running, kill that one first
            if self._scanner_ao_task is not None:
                # stop the analog output task
                daq.DAQmxStopTask(self._scanner_ao_task)

                # delete the configuration of the analog output
                daq.DAQmxClearTask(self._scanner_ao_task)

                # set the task handle to None as a safety
                self._scanner_ao_task = None

            # initialize ao channels / task for scanner, should always be active.
            # Define at first the type of the variable as a Task:
            self._scanner_ao_task = daq.TaskHandle()

            # create the actual analog output task on the hardware device. Via
            # byref you pass the pointer of the object to the TaskCreation function:
            daq.DAQmxCreateTask('ScannerAO', daq.byref(self._scanner_ao_task))
            for n, chan in enumerate(self._scanner_ao_channels):
                # Assign and configure the created task to an analog output voltage channel.
                daq.DAQmxCreateAOVoltageChan(
                    # The AO voltage operation function is assigned to this task.
                    self._scanner_ao_task,
                    # use (all) scanner ao_channels for the output
                    chan,
                    # assign a name for that channel
                    'Scanner AO Channel {0}'.format(n),
                    # minimum possible voltage
                    self._scanner_voltage_ranges[n][0],
                    # maximum possible voltage
                    self._scanner_voltage_ranges[n][1],
                    # units is Volt
                    daq.DAQmx_Val_Volts,
                    # empty for future use
                    '')
        except:
            self.log.exception('Error starting analog output task.')
            return -1
        return 0

    def _stop_analog_output(self):
        """ Stops the analog output.

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_ao_task is None:
            return -1
        retval = 0
        try:
            # stop the analog output task
            daq.DAQmxStopTask(self._scanner_ao_task)
        except:
            self.log.exception('Error stopping analog output.')
            retval = -1
        try:
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_OnDemand)
        except:
            self.log.exception('Error changing analog output mode.')
            retval = -1
        return retval

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of
                                      the clock
        @param string clock_channel: if defined, this is the physical channel
                                     of the clock

        @return int: error code (0:OK, -1:error)
        """
        # The clock for the scanner is created on the same principle as it is
        # for the counter. Just to keep consistency, this function is a wrapper
        # around the set_up_clock.
        return self.set_up_clock(
            clock_frequency=clock_frequency,
            clock_channel=clock_channel,
            scanner=True)

    def set_up_scanner(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        The scanner works pretty much like the counter. Here you connect a
        created clock with a counting task. That can be seen as a gated
        counting, where the counts where sampled by the underlying clock.

        @param list(str) counter_channels: this is the physical channel of the counter
        @param list(str) sources:  this is the physical channel where the photons are to count from
        @param string clock_channel: optional, if defined, this specifies the clock for the counter
        @param list(str) scanner_ao_channels: optional, if defined, this specifies
                                           the analog output channels

        @return int: error code (0:OK, -1:error)
        """
        retval = 0
        if self._scanner_clock_daq_task is None and clock_channel is None:
            print('No clock running, call set_up_clock before starting the counter.')
            return -1

        my_counter_channels = counter_channels if counter_channels else self._scanner_counter_channels
        my_photon_sources = sources if sources else self._photon_sources
        self._my_scanner_clock_channel = clock_channel if clock_channel else self._scanner_clock_channel

        if scanner_ao_channels is not None:
            self._scanner_ao_channels = scanner_ao_channels
            retval = self._start_analog_output()
        self._count_frequency = self._scanner_clock_frequency
        return retval

    def scanner_set_position(self, a0=None, a1=None, a2=None, a3=None):
        """Move stage to a0, a1, a2, a3 (where a is the fourth voltage channel). volts

        #FIXME: No volts
        @return int: error code (0:OK, -1:error)
        """


        if a0 is not None:
            if not(self._scanner_position_ranges[0][0] <= a0 <= self._scanner_position_ranges[0][1]):
                print('You want to set a0 out of range: {0:f}.'.format(a0))
                return -1
            self._current_position[0] = np.float(a0)

        if a1 is not None:
            if not(self._scanner_position_ranges[1][0] <= a1 <= self._scanner_position_ranges[1][1]):
                print('You want to set a1 out of range: {0:f}.'.format(a1))
                return -1
            self._current_position[1] = np.float(a1)

        if a2 is not None:
            if not(self._scanner_position_ranges[2][0] <= a2 <= self._scanner_position_ranges[2][1]):
                print('You want to set a2 out of range: {0:f}.'.format(a2))
                return -1
            self._current_position[2] = np.float(a2)

        if a3 is not None:
            if not(self._scanner_position_ranges[3][0] <= a3 <= self._scanner_position_ranges[3][1]):
                print('You want to set a out of range: {0:f}.'.format(a3))
                return -1
            self._current_position[3] = np.float(a3)

        # the position has to be a vstack
        my_position = np.vstack(self._current_position)

        # then directly write the position to the hardware
        try:
            self._write_scanner_ao(
                voltages=self._scanner_position_to_volt(my_position),
                start=True)
        except:
            return -1
        return 0

    def _write_scanner_ao(self, voltages, length=1, start=False):
        """Writes a set of voltages to the analog outputs.

        @param float[][n] voltages: array of n-part tuples defining the voltage
                                    points
        @param int length: number of tuples to write
        @param bool start: write imediately (True)
                           or wait for start of task (False)

        n depends on how many channels are configured for analog output
        """
        # Number of samples which were actually written, will be stored here.
        # The error code of this variable can be asked with .value to check
        # whether all channels have been written successfully.
        self._AONwritten = daq.int32()
        # write the voltage instructions for the analog output to the hardware
        daq.DAQmxWriteAnalogF64(
            # write to this task
            self._scanner_ao_task,
            # length of the command (points)
            length,
            # start task immediately (True), or wait for software start (False)
            start,
            # maximal timeout in seconds for# the write process
            self._RWTimeout,
            # Specify how the samples are arranged: each pixel is grouped by channel number
            daq.DAQmx_Val_GroupByChannel,
            # the voltages to be written
            voltages,
            # The actual number of samples per channel successfully written to the buffer
            daq.byref(self._AONwritten),
            # Reserved for future use. Pass NULL(here None) to this parameter
            None)
        return self._AONwritten.value

    def _scanner_position_to_volt(self, positions=None):
        """ Converts a set of position pixels to acutal voltages.

        @param float[][n] positions: array of n-part tuples defining the pixels

        @return float[][n]: array of n-part tuples of corresponing voltages

        The positions is typically a matrix like
            [[x_values], [y_values], [z_values], [a_values]]
            but x, xy, xyz and xyza are allowed formats.
        """

        if not isinstance(positions, (frozenset, list, set, tuple, np.ndarray, )):
            print('Given position list is no array type.')
            return np.array([np.NaN])

        vlist = []
        for i, position in enumerate(positions):
            vlist.append(
                (self._scanner_voltage_ranges[i][1] - self._scanner_voltage_ranges[i][0])
                / (self._scanner_position_ranges[i][1] - self._scanner_position_ranges[i][0])
                * (position - self._scanner_position_ranges[i][0])
                + self._scanner_voltage_ranges[i][0]
            )
        volts = np.vstack(vlist)

        for i, v in enumerate(volts):
            if v.min() < self._scanner_voltage_ranges[i][0] or v.max() > self._scanner_voltage_ranges[i][1]:
                print(
                    'Voltages ({0}, {1}) exceed the limit, the positions have to '
                    'be adjusted to stay in the given range.'.format(v.min(), v.max()))
                return np.array([np.NaN])
        return volts

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """
        return self._current_position.tolist()

    def _set_up_line(self, length=100):
        """ Sets up the analog output for scanning a line.

        Connect the timing of the Analog scanning task with the timing of the
        counting task.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            print('Configured analog input is not running, cannot scan a line.')
            return -1

        self._line_length = length
        #Start instance of TimeTagger.CountBetweenMarkers with the correct channels. Does this every time a line is scanned
    
        try:
            # Just a formal check whether length is not a too huge number
            if length < np.inf:

                # Configure the Sample Clock Timing.
                # Set up the timing of the scanner counting while the voltages are
                # being scanned (i.e. that you go through each voltage, which
                # corresponds to a position. How fast the voltages are being
                # changed is combined with obtaining the counts per voltage peak).
                daq.DAQmxCfgSampClkTiming(
                    # add to this task
                    self._scanner_ao_task,
                    # use this channel as clock
                    self._my_scanner_clock_channel + 'InternalOutput',
                    # Maximum expected clock frequency
                    self._scanner_clock_frequency,
                    # Generate sample on falling edge
                    daq.DAQmx_Val_Rising,
                    # generate finite number of samples
                    daq.DAQmx_Val_FiniteSamps,
                    # number of samples to generate
                    self._line_length)

            # Configure Implicit Timing for the clock.
            # Set timing for scanner clock task to the number of pixel.
            daq.DAQmxCfgImplicitTiming(
                # define task
                self._scanner_clock_daq_task,
                # only a limited number of# counts
                daq.DAQmx_Val_FiniteSamps,
                # count twice for each voltage +1 for safety
                self._line_length + 1)
            # Analog channels
            if self._scanner_ai_channels:
                # Analog in channel timebase
                daq.DAQmxCfgSampClkTiming(
                    self._scanner_analog_daq_task,
                    self._scanner_clock_channel + 'InternalOutput',
                    self._scanner_clock_frequency,
                    daq.DAQmx_Val_Rising,
                    daq.DAQmx_Val_ContSamps,
                    self._line_length + 1
                )
        except:
            self.log.exception('Error while setting up scanner to scan a line.')
            return -1
        return 0

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and return the counts on that line.

        @param float[c][m] line_path: array of c-tuples defining the voltage points
            (m = samples per line)
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[m][n]: m (samples per line) n-channel photon counts per second

        The input array looks for a xy scan of 5x5 points at the position z=-2
        like the following:
            [ [1, 2, 3, 4, 5], [1, 1, 1, 1, 1], [-2, -2, -2, -2] ]
        n is the number of scanner axes, which can vary. Typical values are 2 for galvo scanners,
        3 for xyz scanners and 4 for xyz scanners with a special function on the a axis.
        """

        if self._scanner_ai_channels and self._scanner_analog_daq_task is None:
            print('Configured analog input is not running, cannot scan a line.')
            return -1

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            print('Given line_path list is not array type.')
            return np.array([[-1.]])
        try:
            # set task timing to use a sampling clock:
            # specify how the Data of the selected task is collected, i.e. set it
            # now to be sampled by a hardware (clock) signal.
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_SampClk)
            self._set_up_line(np.shape(line_path)[1])
            line_volts = self._scanner_position_to_volt(line_path)
            # write the positions to the analog output
            written_voltages = self._write_scanner_ao(
                voltages=line_volts,
                length=self._line_length,
                start=False)

            # start the timed analog output task
            daq.DAQmxStartTask(self._scanner_ao_task)

            # for i, task in enumerate(self._scanner_counter_daq_tasks):
            #     daq.DAQmxStopTask(task)

            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxConnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel,
                    daq.DAQmx_Val_DoNotInvertPolarity)

            if self._scanner_ai_channels:
                daq.DAQmxStartTask(self._scanner_analog_daq_task)

            daq.DAQmxStartTask(self._scanner_clock_daq_task)


            # wait for the scanner clock to finish
            daq.DAQmxWaitUntilTaskDone(
                # define task
                self._scanner_clock_daq_task,
                # maximal timeout for the counter times the positions
                self._RWTimeout * 2 * self._line_length)
            # stop the clock task
            daq.DAQmxStopTask(self._scanner_clock_daq_task)
            # stop the analog output task
            self._stop_analog_output()

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxDisconnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel)

            #Waits until either the cbm array is fille or until arbitrary 1 second. This is to make sure we are not reading data out before the
            #TimeTagger is able to write from buffer to array. Could maybe sleep in the while loop for 0.1s instead of pass to make it possibly less
            #intensive with the repeated ready() calls to the TimeTagger
            #The actual counts are then retrieved and reshaped. 
            timeout = time.time()
            while (time.time()-timeout)<(1/self._count_frequency * 20):
                pass
            # counts = np.nan_to_num(self.cbm.getData())
            # data = np.reshape(counts,(1, self._line_length))
            # all_data = data * self._count_frequency

            # if self._scanner_ai_channels:
                # all_data[len(self._scanner_counter_channels):] = self._analog_data[:, :-1]

            # update the scanner position instance variable
            self._current_position = np.array(line_path[:, -1])
        except:
            self.log.exception('Error while scanning line.')
            return np.array([[-1.]])
        # return values is a rate of counts/s
        return 0#all_data.transpose()

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        a = self._stop_analog_output()

        b = 0
        if self._scanner_ai_channels:
            try:
                # stop the counter task
                daq.DAQmxStopTask(self._scanner_analog_daq_task)
                # after stopping delete all the configuration of the counter
                daq.DAQmxClearTask(self._scanner_analog_daq_task)
                # set the task handle to None as a safety
                self._scanner_analog_daq_task = None
            except:
                self.log.exception('Could not close analog.')
                b = -1

        c = self.close_counter(scanner=True)
        return -1 if a < 0 or b < 0 or c < 0 else 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return self.close_clock(scanner=True)


    # ======================== Digital channel control ==========================

    def digital_channel_switch(self, channel_name, mode=True):
        """
        Switches on or off the voltage output (5V) of one of the digital channels, that
        can as an example be used to switch on or off the AOM driver or apply a single
        trigger for ODMR.
        @param str channel_name: Name of the channel which should be controlled
                                    for example ('/Dev1/PFI9')
        @param bool mode: specifies if the voltage output of the chosen channel should be turned on or off

        @return int: error code (0:OK, -1:error)
        """
        if channel_name is None:
            print('No channel for digital output specified')
            return -1
        else:

            self.digital_out_task = daq.TaskHandle()
            if mode:
                self.digital_data = daq.c_uint32(0xffffffff)
            else:
                self.digital_data = daq.c_uint32(0x0)
            self.digital_read = daq.c_int32()
            self.digital_samples_channel = daq.c_int32(1)
            daq.DAQmxCreateTask('DigitalOut', daq.byref(self.digital_out_task))
            daq.DAQmxCreateDOChan(self.digital_out_task, channel_name, "", daq.DAQmx_Val_ChanForAllLines)
            daq.DAQmxStartTask(self.digital_out_task)
            daq.DAQmxWriteDigitalU32(self.digital_out_task, self.digital_samples_channel, True,
                                        self._RWTimeout, daq.DAQmx_Val_GroupByChannel,
                                        np.array(self.digital_data), self.digital_read, None)

            daq.DAQmxStopTask(self.digital_out_task)
            daq.DAQmxClearTask(self.digital_out_task)
            return 0


    def pulse_digital_channel(self, channel_name):
        self.digital_channel_switch(channel_name, mode=True)
        self.digital_channel_switch(channel_name, mode=False)