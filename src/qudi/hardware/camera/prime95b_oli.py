import numpy as np

from qudi.interface.camera_interface import CameraInterface

from pyvcam import pvc # Get it here: https://github.com/Photometrics/PyVCAM
from pyvcam.camera import Camera
from pyvcam import constants as const

class Prime95B(CameraInterface):
    """ Hardware class for Prime95B

    Example config for copy-paste:

    mycamera:
        module.Class: 'camera.prime95b.Prime95B'

    """
    # Camera name to be displayed in GUI
    _camera_name = 'Prime95B'


    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self.connect() # connect to camera
        self.set_fan_speed(0) # 0 means high
        self.set_exposure('Internal Trigger')
        self.set_exposure_time(100)
        self._live = False

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # stop acquisition
        # disconnect
        self.disconnect()

    def connect(self):
        """Createsa camera object using the first camera that is found.
        """
        pvc.init_pvcam() # initializes pvcam
        self.cam = next(Camera.detect_camera()) # Generator function to detect a connected camera (specifically: first camera)
        self.cam.open() # open the camera
        return

    def disconnect(self):
        self.cam.close()
        return

    def get_name(self):
        """ Retrieve an identifier of the camera that the GUI can print

        @return string: name for the camera
        """
        name = self.cam.name
        return name

    def get_size(self):
        """ Retrieve size of the image in pixel

        @return tuple: Size (width, height)
        """
        shape = self.cam.shape()
        return shape

    def support_live_acquisition(self):
        """ Return whether or not the camera can take care of live acquisition

        @return bool: True if supported, False if not
        """
        return True

    def start_live_acquisition(self):
        """ Start a continuous acquisition

        @return bool: Success ?
        """
        self.cam.start_live()  
        self._live = True

        return True

    def start_single_acquisition(self):
        """Should start a singel acquisition (specified by interface).

        Not implemented, so won't do anything.

        @return bool: Success ?
        """
        return False

    def stop_acquisition(self):
        """ Stop/abort live or single acquisition

        @return bool: Success ?
        """
        if self._live:
            self._live = False
            self.cam.finish()
        return True

    def get_acquired_data(self):
        """ Return an array of last acquired image.

        @return numpy array: image data in format [[row],[row]...]

        Each pixel might be a float, integer or sub pixels
        """
        image_array = self.cam.get_frame()

        return image_array




    # TOFO: continue here with get_exposure




    def get_fan_speed(self):
        """Returns the fan speed of the camera.
        
        @return int: 0~'High', 1~'Medium', 2~'Low', 3~'Off'
        """
        fan_speed = self.cam.get_param(const.PARAM_FAN_SPEED_SETPOINT)
        return fan_speed

    def set_fan_speed(self, fan_speed):
        """Sets the fan speed of the camera.
        
        @param int fan_speed: 0~'High', 1~'Medium', 2~'Low', 3~'Off'
        """
        fs = {0: 'High', 1: 'Medium', 2: 'Low', 3: 'Off'}
        if fan_speed not in fs.keys():
            raise ValueError(f'Given fan speed {fan_speed} not recognized.')
        self.cam.set_param(const.PARAM_FAN_SPEED_SETPOINT, fan_speed)
        self.log.info(f'Prime95B fan speed: {fs[fan_speed]}')
        if fan_speed==3:
            self.log.warning('Ensure liquid cooling is on!')
        return

    def get_exposure_mode(self):
        """Returns the current exposure mode of the cammera.

        @return str: exp_mode
        """
        exp_mode = self.cam.exp_mode
        return exp_mode

    def set_exposure_mode(self, exp_mode):
        """Sets the exposure to exp_mode passed. Determines trigger behaviour. See constants.py for
        allowed values

        @param exp_mode str: string which is the key to the exposure mode dict in constants.py
        """
        self.cam.exp_mode = exp_mode
        return

    def get_exposure_time(self):
        """Returns the exposure time in ms.
        """
        exp_time = self.cam.exp_time
        exp_res = self.get_exp_res()
        exp_res_dict = {0: 1, 1: 1e-3}
        fac = exp_res_dict[exp_res] # turn us into ms
        exp_time = exp_time*fac
        return exp_time

    def get_max_exposure_time(self):
        max_value_exp_time = self.cam.get_param(const.PARAM_EXPOSURE_TIME,const.ATTR_MAX)
        return max_value_exp_time

    def set_exposure_time(self,exp_time):
        """Sets the exposure time in ms.
        """
        max_value_exp_time = self.get_max_exposure_time()
        if exp_time < 1e-3:
            print(f'exposure time of {exp_time} ns is too small. Setting it to 1 ms.')
            exp_time = 1
            exp_res = 1
        if 1e-3 <= exp_time < 1: # here we need us
            exp_time = int(exp_time * 1e3)
            exp_res = 1
        elif 1 <= exp_time <= max_value_exp_time: # here we need ms
            exp_time = int(exp_time)
            exp_res = 0
        else:
            print(f'exposure time of {exp_time} ns is too big. Setting it to {max_value_exp_time} ms.')
            exp_time = max_value_exp_time
            exp_res = 1
        self._set_exposure_time(exp_time)
        self.set_exposure_res(exp_res)
        return

    def _set_exposure_time(self, exp_time):
        """Set the exposure time to exp_time. Units are given by exp_res_index.
        """
        self.exp_time = self.cam.exp_time = exp_time
        return

    def get_exposure_res(self):
        """Returns exposure resolution index: 0~ms, 1~us
        """
        index = self.cam.exp_res_index
        return index

    def set_exposure_res(self, index):
        """Sets the exposure resolution index.
        
        @param int index:  resolution index: 0~ms, 1~us
            You can check which exposure resolutions are supported by the camera via self.cam.exp_resolutions

        @return bool: True if set sucessfully, False if not
        """

        if index in [0,1] and type(index)==int:
            self.cam.exp_res = index
            return True
        else:
            return False


