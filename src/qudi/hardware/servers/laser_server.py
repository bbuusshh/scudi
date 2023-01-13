from qudi.interface.spectrometer_interface import SpectrometerInterface
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar
from qudi.core.servers import RemoteModulesServer, BaseServer
from qudi.core.module import Base

class LaserServer(Base):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        print('Hello')
    def on_deactivate(self):
        pass