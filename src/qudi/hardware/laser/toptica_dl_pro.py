

from qudi.core.configoption import ConfigOption
from qudi.interface.simple_laser_interface import SimpleLaserInterface
from qudi.interface.simple_laser_interface import ControlMode, ShutterState, LaserState
from enum import IntEnum
import time
from toptica.lasersdk.dlcpro.v2_0_3 import DLCpro,LaserHead,  NetworkConnection, DeviceNotFoundError
import functools
import asyncio


def connect_laser(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with DLCpro(NetworkConnection('169.254.128.41')) as self.dlc:
            res = func(self, *args, **kwargs)
        return res
    return wrapper


class LaserState(IntEnum):
    OFF = 0
    ON = 1

class DlProLaser(SimpleLaserInterface):
    """ ToDo: describe

    Example config for copy-paste:

    dl_pro:
        module.Class: 'laser.toptica_dl_pro.DlProLaser'
        tcp_address: '169.254.128.41'
        current_range: [0, 90]
    """

    tcp_address = ConfigOption(name='tcp_address', missing='error')
    current_range = ConfigOption(name='current_range', default=(0, 90), missing='warn')
    # max = ConfigOption(name='maxpower', default=0.250, missing='warn')
   

    def on_activate(self):
        """ Activate module.
        """
        
        self.get_laser_state()

    def on_deactivate(self):
        """ Deactivate module.
        """
        return 

    @connect_laser
    def get_current_setpoint(self):
        """ Get laser current setpoint

        @return float: laser current setpoint
        """
        return self.dlc._laser1.dl.cc.current_set.get()

    @connect_laser
    def set_current(self, current):
        """ Set laser current setpoint

        @param float current: desired laser current setpoint
        set current in mA
        """
       
        self.dlc._laser1.dl.cc.current_set.set(current)

    @connect_laser
    def set_laser_state(self, state):
        """ Set laser state.

        @param LaserState state: desired laser state enum

        dlc is instantianed in the decorator
        """
        return self.dlc._laser1.dl.cc.enabled.set(bool(state))

    @connect_laser
    def get_laser_state(self):
        """ Get laser state

        @return LaserState: current laser state
        """
        return int(self.dlc._laser1.dl.cc.enabled.get())

    @connect_laser
    def get_current(self):
        """ Get actual laser current

        @return float: laser current in current units
        """
        return self.dlc._laser1.dl.cc.current_set.get()


    def get_current_range(self):
        """ Get laser current range.

        @return float[2]: laser current range
        """
        return self.current_range

    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit
        """
        return "mA"

    def get_power_range(self):
        """ Return laser power range

        @return float[2]: power range (min, max)
        """
        return (0,1)

    
    def get_power(self):
        """ Return actual laser power

        @return float: Laser power in watts
        """
        return 0

    
    def set_power(self, power):
        """ Set power setpoint.

        @param float power: power to set
        """
        pass


    def get_power_setpoint(self):
        """ Return laser power setpoint.

        @return float: power setpoint in watts
        """
        return 0
 


    def allowed_control_modes(self):
        """ Get supported control modes

        @return frozenset: set of supported ControlMode enums
        """
        return {ControlMode.CURRENT}

 
    def get_control_mode(self):
        """ Get the currently active control mode

        @return ControlMode: active control mode enum
        """
        return ControlMode.CURRENT

  
    def set_control_mode(self, control_mode):
        """ Set the active control mode

        @param ControlMode control_mode: desired control mode enum
        """
        return ControlMode.CURRENT


    def get_shutter_state(self):
        """ Get laser shutter state

        @return ShutterState: actual laser shutter state
        """
        return ShutterState.NO_SHUTTER

 
    def set_shutter_state(self, state):
        """ Set laser shutter state.

        @param ShutterState state: desired laser shutter state
        """
        pass

   
    def get_temperatures(self):
        """ Get all available temperatures.

        @return dict: dict of temperature names and value in degrees Celsius
        """
        return {"Laser": 0}

    
    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        pass
