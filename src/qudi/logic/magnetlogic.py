import numpy as np

from qudi.core.module import LogicBase

class MagnetLogic(LogicBase):
    ## connectors

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def on_activate(self):
        pass


    def on_deactivate(self):
        pass


    def _start_scan(self, params):
        """Scans the magnetic field along the given axes.
        
        @input array params: 2D array specifying the axes:
            [[axis0_start, axis0_stop, axis0_steps],
                [axis1_start, axis1_stop, axis1_steps],
                [axis2_start, axis2_stop, axis2_steps]]
        """
        scanning_matrix = self.build_scanning_matrix(params)
        self.scan_along_matrix(scanning_matrix)
        return


    def build_scanning_matrix(self, params):
        """Builds 4D-matrix for scanning along three axes.
        
        first three indices are axes, last index is pixel.
        Example for scan in x y and z
        [
            [   [[x0,y0,z0],[x0,y0,z1]],
                [[x0,y1,z0],[x0,y1,z1]],
                [[x0,y2,z0],[x0,y2,z1]]
            ],
            [   [[x1,y0,z0],[x1,y0,z1]],
                [[x1,y1,z0],[x1,y1,z1]],
                [[x1,y2,z0],[x1,y2,z1]]
            ]
        ]
        Most inner block (axes 0 to 2) is last index, second most inner block ist third axis,
        outer block ist first axis. 
        To scan the first axis, you need to vary the first index,
        to scan the second axis you need to vary the second index
        and to scan the third axis you need to vary the third index.
        """


        # TODO: get rid of the matrix thingy.
        # Instead built a 2d matrix where each line is one pixel. 
        # By going through the stack you will scan each pixel in the correct order.
        # Choosing the next pixel is really easy, just pop the last element.
        """
        [   [x0,y0,z0],
            [x1,y0,z0],
            [x0,y1,z0],
            [x1,y1,z0],
            [x0,y2,z0],
            [x1,y2,z0],
            [x0,y0,z1],
            [x1,y0,z1],
            [x0,y1,z1],
            [x1,y1,z1],
            [x0,y2,z1],
            [x1,y2,z1]
        ]
        """


        # create axes
        axes = []
        for i in range(3):
            start,stop,steps = params[i,:]
            steps = int(steps)
            axis = np.linspace(start,stop,steps)
            axes.append(axis)
        axes = np.array(axes, dtype=object)
        # figure out dimension of each axis 
        dims = [len(ax) for ax in axes]
        dims.append(3)
        # built scanning matrix
        scanning_matrix = np.zeros(dims)
        ax = 0
        reps = [dims[2],dims[1],1]
        scanning_matrix[:,:,:,ax] = np.transpose(np.tile(axes[ax],reps),(2,1,0))
        ax = 1
        reps = [dims[2],dims[0],1]
        scanning_matrix[:,:,:,ax] = np.transpose(np.tile(axes[ax],reps),(1,2,0))
        ax = 2
        reps = [dims[0], dims[1], 1]
        scanning_matrix[:,:,:,ax] = np.transpose(np.tile(axes[ax],reps),(0,1,2))
        return scanning_matrix


    def scan_along_matrix(self, scanning_matrix):
        # ramp field
        # once done (signal) take counts for XY seconds
        # ramp field again
        print(f'scanning along the following matrix: {scanning_matrix}')
        pass