import numpy as np
from qtpy import QtCore
from datetime import datetime

from qudi.core.module import Base
from qudi.core.connector import Connector


class magnet_3d(Base):
    # declare connector
    # Note: you must create the interface file and give it to the class in the hardware file.
    # magnet_x = Connector(interface='Magnet1DInterface')
    # magnet_y = Connector(interface='Magnet1DInterface')
    # magnet_z = Connector(interface='Magnet1DInterface')
    magnet_x = Connector(interface='AMI430')
    magnet_y = Connector(interface='AMI430')
    magnet_z = Connector(interface='AMI430')

    B_max = ConfigOption(name='B_max', missing='warn')
    Bz_max = ConfigOption(name='Bz_max', missing='warn')

    #internal signals
    sigFastRamp = QtCore.Signal()
    sigSlowRamp = QtCore.Signal()

    # external signals
    sigRampFinished = QtCore.Signal()


    def on_activate(self):
        self._magnet_x = self.magnet_x()
        self._magnet_y = self.magnet_y()
        self._magnet_z = self.magnet_z()

        # Would be nice if we could get the dict directly from the config
        self.constraints = { 
            'B_max' : self.B_max,
            'Bz_max' : self.Bz_max
        }

        # connect internal signals
        self.sigFastRamp.connect(self._fast_ramp_loop_body)
        self.sigSlowRamp.connect(self._slow_ramp_loop_body)

        self.debug = True

        # TODO: Get values from config
        self._abortRampLoop = False
        self.rampTimerInterval = 10000
        self.fastRampTimerInterval = 10000
        self.slowRampTimerInterval = 10000
        self._abortRampToZeroLoop = False
        self.rampToZeroTimerInterval = 10000
        return


    def  on_deactivate(self):
        self._magnet_x.on_deactivate()
        self._magnet_y.on_deactivate()
        self._magnet_z.on_deactivate()
        return

    
    def ramp(self, field_target=[None,None,None], enter_persistent=False):
        """Ramps the magnet."""
        # check if the target field is within constraints
        if self.check_field_amplitude(field_target) != 0:
            raise RuntimeError('Entered field is too strong.')
        # check the path between the fields
        current_field = self.get_field()
        combined_field = self.combine_fields(field_target,current_field)
        ret = self.check_field_amplitude(combined_field)
        # store enter_persistent for later use
        self.enter_persistent = enter_persistent
        # ramp according to the result from the check
        self._abortRampLoop = False
        self._abortRampToZeroLoop = True
        if ret == 0:
            self.fast_ramp(field_target=field_target)
            self.sigFastRamp.emit()
            return
        else:
            # order the axes by ascending field strength
            indices = np.argsort(field_target)
            self.order_axes = []
            self.field_target_reordered = []
            for i in indices:
                if i == 0:
                    self.order_axes.append('x')
                elif i == 1:
                    self.order_axes.append('y')
                elif i == 2:
                    self.order_axes.append('z')
                self.field_target_reordered.append(field_target[i])
            # start ramping of the first axis
            self.current_axis = self.order_axes.pop(0)
            self.current_axis_field_target = self.field_target_reordered.pop(0)
            cmd = f'self._magnet_{self.current_axis}.ramp(field_target={self.current_axis_field_target})'
            eval(cmd)
            self.sigSlowRamp.emit()
            return

        
    def abort_ramp(self):
        """Aborts the ramp.
        
        Aborts the ramp loops and pauses the ramp.
        """
        self._abortRampLoop = True
        self.pause_ramp()
        return


    def get_field(self):
        """Returns field in x,y,z direction."""
        field_x = self._magnet_x.get_field()
        field_y = self._magnet_y.get_field()
        field_z = self._magnet_z.get_field()
        return[field_x,field_y,field_z]


    def check_field_amplitude(self,target_field):
        """Checks if the given field exceeds the constraints.
        
        Returns 0 if everything is okay, returns -1 if field is too strong.
        """

        target_amplitude = np.linalg.norm(target_field)
        max_amplitude = self.constraints['B_max']
        max_z_amplitude = self.constraints['Bz_max']
        if target_amplitude > max_amplitude and target_field[0] !=0 and target_field[1] != 0:
            # vector field too high
            return -1
        elif abs(target_field[2]) > max_z_amplitude:
            # z field too high
            return -1
        else:
            return 0


    def combine_fields(field1,field2):
        """Combines the given fields.
        
        Combined field is max of individual fields.
        e.g. [1,2,3] and [2,2,2] would result in [2,2,3].
        """
        l1 = len(field1)
        l2 = len(field2)
        if l1 != l2:
            raise RuntimeError('GIven fields are not of the same length.')
        field_combined = []
        for i in range(l1):
            field_combined.append(max(field1[i],field2[i]))
        return field_combined


    def _fast_ramp_loop_body(self):
        """Loop that controls the ramping of the magnet.
        
        If target field has been reached and magnet is in holding mode, sigRampFinished is emitted.
        Otherwise it is called again later.
        """
        # abort ramp loop if requested
        if self._abortRampLoop:
            self.pause_ramp()
            return 
        ramping_state = self.get_ramping_state()
        if ramping_state == [2,2,2]: # might be a problem with pause?
            self._abortRampLoop = True
            self.sigRampFinished.emit()
            return
        else:
            QtCore.QTimer.singleShot(self.fastRampTimerInterval, self.sigFastRamp.emit())
            return


    def _slow_ramp_loop_body(self):
        # abort ramp loop if requested
        if self._abortRampLoop:
            self.pause_ramp()
            return
        # get index of current axis
        axis = self.current_axis
        if axis == 'x':
            index = 0
        if axis == 'y':
            index = 1
        if axis == 'z':
            index = 2
        ramping_state = self.get_ramping_state()
        if ramping_state[index] == 2: #HOLDING
            if len(self.order_axes) > 0:
                # go to next axis
                self.current_axis = self.order_axes.pop(0)
                self.current_axis_field_target = self.field_target_reordered.pop(0)
                cmd = f'self._magnet_{self.current_axis}.ramp(field_target={self.current_axis_field_target})'
                eval(cmd)
                return
            else:
                # ramping done on all three axes
                self._abortRampLoop = True
                self.sigRampFinished.emit()
                return
        else: # we are not holding --> still ramping
            # might be a problem with ramping to zero
            QtCore.QTimer.singleShot(self.slowRampTimerInterval, self.sigSlowRamp.emit())
            return


    def fast_ramp(self, field_target):
        self._magnet_y.ramp(field_target = field_target[1])
        self._magnet_x.ramp(field_target = field_target[0])
        self._magnet_z.ramp(field_target = field_target[2])
        return 0

    
    def get_ramping_state(self):
        """Returns the ramping state of all three 1D magnets.
        
        integers mean the following:
            1:  RAMPING to target field/current
            2:  HOLDING at the target field/current
            3:  PAUSED
            4:  Ramping in MANUAL UP mode
            5:  Ramping in MANUAL DOWN mode
            6:  ZEROING CURRENT (in progress)
            7:  Quench detected
            8:  At ZERO current
            9:  Heating persistent switch
            10: Cooling persistent switch

        @return: list of ints with ramping status [status_x,status_y,status_z].
        """
        status_x = self._magnet_x.get_ramping_state()
        status_y = self._magnet_y.get_ramping_state()
        status_z = self._magnet_z.get_ramping_state()
        status = [status_x,status_y,status_z]
        return status


    def continue_ramp(self):
        """Resumes ramping.
        
        Puts the power supply in automatic ramping mode. Ramping resumes until target field/current is reached.
        """
        self._magnet_x.continue_ramp()
        self._magnet_y.continue_ramp()
        self._magnet_z.continue_ramp()
        return


    def pause_ramp(self):
        """Pauses the ramping process.
        
        The current/field will stay at the level it has now.
        """
        self.abort_ramp()
        self._magnet_x.pause_ramp()
        self._magnet_y.pause_ramp()
        self._magnet_z.pause_ramp()
        return


    def ramp_to_zero(self):
        """Ramps the magnet to zero field and turns of the PSW heaters."""
        self._abortRampLoop = True
        self._abortRampToZeroLoop = False
        self._ramp_to_zero_loop(first_time=True)
        return