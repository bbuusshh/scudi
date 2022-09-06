import numpy as np

from qudi.core.module import LogicBase

class MagnetLogic(LogicBase):
    ## connectors

    def __init__(self):
        pass

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass


    def build_scan_lines(self, params):
        """Builds 4D-matrix for scanning along three axes.
        
        first three indices are axes, last index is pixel.
        Example for scan in x y and z
        [
            [   [[x0,y0,z0],[x1,y0,z0]],
                [[x0,y1,z0],[x1,y1,z0]],
                [[x0,y2,z0],[x1,y2,z0]]
            ],
            [   [[x0,y0,z1],[x1,y0,z1]],
                [[x0,y1,z1],[x1,y1,z1]],
                [[x0,y2,z1],[x1,y2,z1]]
            ]
        ]
        """
 
        dims = params[:,2]
        dims = np.append(dims,3) # each pixel consists of 3 coordinates
        # built axes
        axes = np.zeros(3)
        for i in range(3):
            axes[i] = np.linspace(params[i,0],params[i,1],params[i,2])
        # create matrix for scanning positions
        scanning_matrix = np.ones(dims)
        # fill in values for axis 0
        for i in range(dims[0]):
            scanning_matrix[i,:,:,0] = axes[i]
        # fill in values for axis 1
        for i in range(dims[1]):
            scanning_matrix[:,i,:,1] = axes[i]
        # fill in values for axis 2
        for i in range(dims[2]):
            scanning_matrix[:,:,i,2] = axes[i]
        print(f'Scanning matrix: \n {scanning_matrix}')