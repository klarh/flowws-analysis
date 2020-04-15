import flowws
from flowws import Argument as Arg
import plato.draw

from ._diffraction_primitive import Diffraction as DiffractionPrimitive
from ._diffraction_primitive import DEFAULT_COLORMAP

@flowws.add_stage_arguments
class Diffraction(flowws.Stage):
    """Compute a 3D diffraction pattern of the system and display its slice or projection.

    This stage computes a 3D histogram of the system based on the
    given periodic system box and particle coordinates and performs
    the FFT in 3D. Either a slice or full projection through the
    Fourier space is displayed with the current system orientation.

    **Note:** This module should be considered experimental in terms
    of stability for the time being; the inputs and outputs may change
    drastically in the future, or the module may be removed entirely.
    """
    ARGS = [
        Arg('bin_count', '-b', int, default=128,
            help='Number of bins to use in the x, y, and z directions'),
        Arg('projection', '-p', bool, False,
            help='If True, project the diffraction pattern all the way through fourier space'),
        Arg('min_value', None, float, 0,
            help='Minimum value of intensity to clip to'),
        Arg('max_value', None, float, 1,
            help='Maximum value of intensity to clip to'),
        Arg('sigma', None, float, 0,
            help='Lengthscale of blurring the FFT'),
    ]

    def run(self, scope, storage):
        """Prepare to display the diffraction pattern"""
        self.positions = scope['position']
        self.box = scope['box']
        scope.setdefault('visuals', []).append(self)
        scope.setdefault('visual_link_rotation', []).append(self)

    def draw_plato(self):
        prim = DiffractionPrimitive(positions=self.positions, box=self.box)
        prim.size = self.arguments['bin_count']
        prim.sigma = self.arguments['sigma']
        prim.vmin = self.arguments['min_value']
        prim.vmax = self.arguments['max_value']
        prim.projection = self.arguments['projection']
        prim.cmap = DEFAULT_COLORMAP

        return plato.draw.Scene(prim, size=(1, 1), pixel_scale=800)
