import ni_card

class DyeLaserController():
    def __init__(self):
        self.ni = ni_card.NationalInstruments()
    def set_thin_etalon_voltage(self,v):
        self.ni.scanner_set_position(a2 = v)
    def set_motor_direction(self,sign):
        if sign > 0:
            self.ni.scanner_set_position(a2 = 5)
        elif sign < 0 :
            self.ni.scanner_set_position(a1=-5)
    def move_motor_pulse(self):
        self.ni.pulse_digital_channel(self.ni._stepper_pulse_channel)