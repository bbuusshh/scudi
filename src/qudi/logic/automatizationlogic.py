"""
Example config:

    automatization_logic:
        module.Class: 'automatizationlogic.Automatedmeasurements'
        connect:
            spectrometergui: 'spectrometer'
            optimizerlogic: 'scanning_optimize_logic'
            spectrometerlogic: 'spectrometerlogic'
            poimanagerlogic: 'poi_manager_logic'
            switchlogic: 'switchlogic'

"""
from pydoc import doc
from qtpy import QtCore
import inspect
import time

from qudi.core.module import LogicBase
from qudi.core.connector import Connector

class Automatedmeasurements(LogicBase):
    ## declare connectors
    spectrometergui = Connector(name='spectrometergui', interface='SpectrometerGui')
    optimizerlogic = Connector(name='optimizerlogic', interface='ScanningOptimizeLogic')
    spectrometerlogic = Connector(name='spectrometerlogic',interface='SpectrometerLogic')
    poimanagerlogic = Connector(name='poimanagerlogic',interface='PoiManagerLogic')
    switchlogic = Connector(name='switchlogic',interface='SwitchLogic')

    # internal signals
    sigNextPoi = QtCore.Signal()
    sigNextStep = QtCore.Signal()

    # external signals
    sigSaveSpectrum = QtCore.Signal()
    sigSwitchStatus = QtCore.Signal(str,str) # switch, state


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # dictionary of functions
        self.func_dict = {
            'move' : self.move_to_poi,
            'optimize' : self.optimize_on_poi,
            'spectrum' : self.take_spectrum,
            'blue_on' : self.turn_on_blue_laser,
            'blue_off' : self.turn_off_blue_laser
        }

        ## init variables
        self.abort = False
        self.steps = []
        self.debug = True # prints for debugging

        # init variables that tell teh script if certain measurement was started here
        # (to make sure we don't catch signals when we don't want to)
        self._optimizer_started = False
        self._spectrum_started = False
        self._blue_is_on = None # status of blue laser (True: blue laser shines on sample, False: it does not)

        return


    def on_activate(self):
        """properly activates the module.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._spectrometer_gui = self.spectrometergui()
        self._optimizer_logic = self.optimizerlogic()
        self._spectrometer_logic = self.spectrometerlogic()
        self._poimanager_logic = self.poimanagerlogic()
        self._switch_logic = self.switchlogic()

        # connect internal signals
        self.sigNextPoi.connect(self._next_poi, QtCore.Qt.QueuedConnection)
        self.sigNextStep.connect(self._next_step, QtCore.Qt.QueuedConnection )

        # connect external signals
        self._optimizer_logic.sigOptimizeDone.connect(self._optimization_done, QtCore.Qt.QueuedConnection)
        self._spectrometer_logic.sigSpectrumDone.connect(self._spectrum_done)

        self.sigSaveSpectrum.connect(self._spectrometer_gui.save_spectrum, QtCore.Qt.QueuedConnection)
        self.sigSwitchStatus.connect(self._switch_logic.set_state, QtCore.Qt.QueuedConnection)


    def on_deactivate(self):
        """Properly deactivates the module.
        """
        pass


    def start(self, steps, shift=None):
        """Starts the measurement series on all pois.

        @param list steps: list of the steps (as string) that wil be performed.

        @param array shift: Shift between the position of the defects on the scan and the actual position of the defects.
            actual_position = scan_position + shift
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')

        # initialize pois and steps
        self.init_pois(shift)
        self.init_steps(steps)
        
        self.abort = False
        self.sigNextPoi.emit()
        return

    def stop(self):
        """Stops the measurement series.
        
        Finishes the current measurement and then stops.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self.abort = True
        return


    def init_pois(self,shift=None):
        """initializes the pois.
        
        Get the name and position of the pois. Stores it in list.

        @param array shift: Shift between the position of the defects on the scan and the actual position of the defects.
            actual_position = scan_position + shift
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        # get poin maes from poimanagerlogic and store them as class objects
        self.poi_names = self._poimanager_logic.poi_names
        # copy poi names in array that we can modify (shallow copy)
        self._poi_names = self.poi_names.copy()
        # get positions of the pois (dict)
        poi_positions = self._poimanager_logic.poi_positions
        # shift them if a shift was given
        if shift != None:
            for key in poi_positions.keys():
                # add shift to position
                poi_positions[key] = poi_positions[key] + shift
        # store poi positions as class object
        self.poi_positions = poi_positions
        return


    def init_steps(self, steps):
        """Stores the individual steps (measurements) for the POIs as class objects.

        @param list steps: list of the individual step names (as str).
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        keys = self.func_dict.keys()
        if not set(steps).issubset(set(keys)):
            raise Exception(f'The following steps are not listed in the func_dict: {list(set(steps) - set(keys))}. \nKeeping old steps.')
        self.steps = steps
        return


    def _next_poi(self):
        """Iterates through the pois.
        
        Sets the next poi to be the active one and starts the measurements on this one.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        # Stop program if finished or user wants to stop
        if self.abort or (len(self._poi_names)==0):
            if self.debug:
                print(f'Stopping pois. Abort was set to {self.abort} and {len(self._poi_names)} pois were left.')
            self.abort = True
            return
        # Choose the first poi in the list, set it as the current one and delete it.
        self._current_poi_name = self._poi_names.pop(0)
        if self.debug:
            print('Current poi %s'%self._current_poi_name)
        # updates the position of the current poi
        self._current_poi_position = self.poi_positions[self._current_poi_name]
        
        # copy the steps into an array that we can modify (shallow copy)
        self._steps = self.steps.copy()
        if self.debug:
            print(f'Steps are {self._steps}.')
        # start the steps
        self.sigNextStep.emit()
        return


    def _next_step(self):
        """Iterates through the steps.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        # Stop the program if user wants to stop.
        if self.abort:
            if self.debug:
                print('Stopping steps.')
            return
        if len(self._steps) == 0:
            # all steps for the current poi are done, go to next poi
            if self.debug:
                print('All steps are done, moving to next poi.')
            self.sigNextPoi.emit()
            return
        # choose next step in list as current one and remove it
        self._current_step = self._steps.pop(0)
        if self.debug:
            print(f'Current step: {self._current_step}.')
        #run the step
        self.func_dict[self._current_step]()
        return


    def move_to_poi(self, poi_name=None):
        """Moves the focus to the poi.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}, poi_name {poi_name}')
        if poi_name==None:
            poi_name = self._current_poi_name
        # go to poi
        self._poimanager_logic.go_to_poi(name=poi_name)
        # poimanager does not send signal once point is reached. 
        # We will wait for a bit and send a signal ourselves (we are assuming 0.1s is enough)
        time.sleep(0.1)
        self.sigNextStep.emit()
        return


    def optimize_on_poi(self):
        """optimizes on the poi.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._optimizer_started = True
        self._optimizer_logic.start_optimize()
        return


    def _optimization_done(self):
        """Catches the signal from the optimizerlocig that the optimization is done.

        Only does something if self._optimizer_started was set to True by the logic.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}, _optimizer_started = {self._optimizer_started}')
        if self._optimizer_started == True:
            # make sure we only do sth with the signal if we initialized the measurement
            self._optimizer_started = False
            self.sigNextStep.emit()
            return
        else:
            return


    def take_spectrum(self):
        """Tells the spectrumlogic to start taking the spectrum.

        Following settings are used:
        No constant acquisition, background correction, no differential spectrum, automatic flip
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        if not self._spectrometer_logic.acquisition_running:
            self._spectrum_started = True
            # set parameters
            self._spectrometer_logic.background_correction = True
            self._spectrometer_logic.constant_acquisition = False
            self._spectrometer_logic.differential_spectrum = False
            self._spectrometer_logic.do_flip = True
            # acquire the spectrum
            self._spectrometer_logic._sig_get_spectrum.emit(False,False,True) # constant_acquisition, differential_spectrum, reset
            return
        else:
            raise Exception('spectrum acquisition already running.')


    def _spectrum_done(self):
        """Catches the signal from the spectrometerlogic that the spectrum is taken and saves the spectrum.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}, _spectrum_started = {self._spectrum_started}')
        if self._spectrum_started:
            name_tag = f'defect-name-{self._current_poi_name}_blue-on-{self._blue_is_on}'
            self.save_spectrum(name_tag)
            self.sigNextStep.emit()
        else:
            return

    
    def save_spectrum(self,name_tag=None):
        """Saves the acquired spectrum.

        You need to have the gui for the spectrometer active and set all the parameters (apart from the nametag).
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}, name = {name_tag}')
        # This is really ugly but also the fastest way to make it work
        # set parameters in gui
        self._spectrometer_gui.save_widget.saveTagLineEdit.setText(name_tag)
        # hit save
        self.sigSaveSpectrum.emit()
        return
        

    def turn_on_blue_laser(self):
        """Turns on the blue laser.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._blue_is_on = True
        self.sigSwitchStatus.emit('Laser405nm', 'On')
        time.sleep(0.1)
        self.sigNextStep.emit()
        return


    def turn_off_blue_laser(self):
        """Turns off the blue laser.
        """
        if self.debug:
            print(f'{__name__}, {inspect.stack()[0][3]}')
        self._blue_is_on = False
        self.sigSwitchStatus.emit('Laser405nm', 'Off')
        time.sleep(0.1)
        self.sigNextStep.emit()
        return