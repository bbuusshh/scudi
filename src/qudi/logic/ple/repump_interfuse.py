# -*- coding: utf-8 -*-
"""
This file contains a qudi logic module template

Copyright (c) 2021, the qudi developers. See the AUTHORS.md file at the top-level directory of this
distribution and on <https://github.com/Ulm-IQO/qudi-iqo-modules/>

This file is part of qudi.

Qudi is free software: you can redistribute it and/or modify it under the terms of
the GNU Lesser General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later version.

Qudi is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with qudi.
If not, see <https://www.gnu.org/licenses/>.
"""

from ast import Raise
from email.policy import default
from qudi.core.connector import Connector
from qudi.core.module import LogicBase
from qudi.core.configoption import ConfigOption
from qudi.logic.pulsed.pulse_objects import PulseBlockElement, PulseBlock, PulseBlockEnsemble
from qudi.logic.pulsed.sampling_functions import SamplingFunctions
from PySide2 import QtCore
from qudi.core.statusvariable import StatusVar

class RepumpInterfuseLogic(LogicBase):
    sigParamsUpdated = QtCore.Signal(str, dict,  QtCore.Qt.QueuedConnection)
    _pulsed = Connector(name='pulsed', interface='PulsedMasterLogic')
    _resonant_laser = ConfigOption(name='resonant_laser', default=None)
    _repump_laser = ConfigOption(name='repump_laser', default=None)
    ensembles = []
    trigger_channel = 'd_ch5'
    resonant_block = None
    trigger_block = None
    default_params = {
        "resonant":
            {   
                "enabled": False,
                "pulsed" : True,
                "length" : 30e-9,
                "period" : 150e-9,
                "power"  : 1
            },
        "repump":
            {   
                "enabled": False,
                "pulsed" : True,
                "length" : 30e-9,
                "delay"  : 150e-9,
                "power"  : 1,
            },
        }
    parameters = StatusVar(name="_parameters", default=default_params)
    
    def on_activate(self):
        self.pulsed = self._pulsed()
        if self._resonant_laser is not None:
            self.resonant_block = None#self.create_pulse_block(channels = list(self._resonant_lasers.values()))
        self.a_ch ={
        'a_ch1': SamplingFunctions.Idle(),
        'a_ch2': SamplingFunctions.Idle(),
    }
        self.d_ch = {
            'd_ch1': False, 
            'd_ch2': False, 
            'd_ch3': False, 
            'd_ch4': False,
            }
        

        
    def update_params(self):
        self.sigParamsUpdated.emit('repump', self.parameters)
        self.sigParamsUpdated.emit('resonant', self.parameters)
    
    def on_deactivate(self):
        pass
    
    def setup_resonant_block(self):
        return self.resonant_block

    def create_pulse_block(self, name, length, wait, delay = None, channels = ['d_ch1']):
        elements= []
        d_ch = self.d_ch.copy()
        tuple(d_ch.update({ch: True})  for ch in channels)
        if delay is not None:
            delay_block = PulseBlockElement(
                init_length_s=wait, #in sec
                increment_s=0, 
                pulse_function=self.a_ch,
                digital_high=self.d_ch, 
                laser_on=False
                )
            elements.append(delay_block)
        pulse_block = PulseBlockElement(
            init_length_s=length, 
            increment_s=0, 
            pulse_function=self.a_ch, 
            digital_high=d_ch, 
            laser_on=False
        )
        elements.append(pulse_block)
        wait_block = PulseBlockElement(
            init_length_s=wait, 
            increment_s=0, 
            pulse_function=self.a_ch,
            digital_high=self.d_ch, 
            laser_on=False
            )
        elements.append(wait_block)
        pulse_block = PulseBlock(name=name, element_list=elements)
        self.pulsed.sigSavePulseBlock.emit(pulse_block)

        return pulse_block

    def create_block_ensemble(self, name, block_list):
        block_ensemble = PulseBlockEnsemble(name=name, block_list=block_list, rotating_frame=False)
        self.pulsed.sigSaveBlockEnsemble.emit(block_ensemble)
        self.ensembles.append(block_ensemble.name)
        return block_ensemble

    def enable_pulsed(self, enabled, ensemble_name):
        self.pulsed.sigSampleBlockEnsemble.emit(ensemble_name)
        self.pulsed.sigLoadBlockEnsemble.emit(ensemble_name) 
        self.pulsed.sigPulserRunningUpdated.emit(enabled)    

    def create_pulse(self, length, delay, name, channels = ['d_ch1']):
        pulse_block = self.create_pulse_block(length, delay, name, channels = ['d_ch1'])
        block_ensemble = self.create_block_ensemble(f"{name}_ensemble", [(pulse_block.name, 0)])
        return block_ensemble

    def repump_updated(self, params):
        self.parameters['repump'].update(params)
        return 
    
    def pulser_updated(self, params):
        self.parameters['resonant'].update(params)
        self.check_period()
        return 
    def check_period(self):
        new_period = self.parameters['resonant']['length'] + self.parameters['repump']['delay'] + self.parameters['repump']['length']
        
        if new_period > self.parameters['resonant']['period']:
            self.parameters['resonant']['period'] = new_period
        self.sigParamsUpdated.emit('resonant', self.parameters)

    def repump_enabled(self, enabled):
        self.parameters['repump'].update({"enabled":enabled })
        if self.parameters['repump']['enabled']:
            self.run_ensemble()
        return 
    
    def pulser_enabled(self, enabled):
        self.parameters['resonant'].update({"enabled":enabled })
        if self.parameters['resonant']['enabled']:
            self.run_ensemble()
        return 

    def pulser_pulsed(self, pulsed):
        self.parameters['resonant'].update({"pulsed":pulsed })
        return 
    
    def repump_pulsed(self, pulsed):
        self.parameters['repump'].update({"pulsed":pulsed })
        return 
    
    def run_ensemble(self, ensemble_name = 'resonant repumped'):
        self.construct_resonant_and_repump_ensemble()
        self.pulsed.sigLoadBlockEnsemble.emit(ensemble_name) 
        self.pulsed.sigSampleBlockEnsemble.emit(ensemble_name)
        self.pulsed.sigPulserRunningUpdated.emit(self.parameters['repump']['enabled'] and self.parameters['resonant']['enabled']) 

    def construct_resonant_and_repump_ensemble(self):
        period_exceeded = self.parameters['resonant']['period'] > self.parameters['resonant']['length'] + self.parameters['repump']['delay'] + self.parameters['repump']['length']
        if period_exceeded:
            return 
        self.pulsed.sigDeletePulseBlock.emit('resonant repumped')
        self.pulsed.sigDeleteBlockEnsemble.emit('resonant repumped')
        element_list = []
        d_ch = self.d_ch.copy()
        d_ch.update({self._resonant_laser: self.parameters['resonant']['enabled']}) 
        resonant_pulse_block = PulseBlockElement(
            init_length_s=self.parameters['resonant']['length'], 
            increment_s=0, 
            pulse_function=self.a_ch, 
            digital_high=d_ch, 
            laser_on=False
        )
        # now the delay until the repump
        #  
        element_list.append(resonant_pulse_block)

        delay_pulse_block = PulseBlockElement(
            init_length_s=self.parameters['repump']['delay'], 
            increment_s=0, 
            pulse_function=self.a_ch, 
            digital_high=self.d_ch, #all off
            laser_on=False
        )
        element_list.append(delay_pulse_block)
        #now repump length
        d_ch = self.d_ch.copy()
        d_ch.update({self._repump_laser: self.parameters['repump']['enabled']}) 
        repump_pulse_block = PulseBlockElement(
            init_length_s=self.parameters['repump']['length'], 
            increment_s=0, 
            pulse_function=self.a_ch, 
            digital_high=d_ch,
            laser_on=False
        )
        element_list.append(repump_pulse_block)
        #now the nothing till the priod ends
        time_off = self.parameters['resonant']['period'] - self.parameters['resonant']['length'] - self.parameters['repump']['delay'] - self.parameters["repump"]['length']
        if time_off < 0 :
            raise ValueError('Period is too short') 
        off_pulse_block = PulseBlockElement(
            init_length_s = time_off, 
            increment_s=0, 
            pulse_function=self.a_ch, 
            digital_high=self.d_ch,  # all off
            laser_on=False
        )
        element_list.append(off_pulse_block)

        pulse_block = PulseBlock(name='resonant repumped', element_list=element_list)
        self.pulsed.sigSavePulseBlock.emit(pulse_block)

        block_ensemble = PulseBlockEnsemble(name='resonant repumped', block_list=[(pulse_block.name, 0)], rotating_frame=False)
        self.pulsed.sigSaveBlockEnsemble.emit(block_ensemble)
    
        