
import flowws
from flowws import Argument as Arg
import plato
import numpy as np

def center(box, positions, target=(0, 0, 0)):
    """Centers a set of positions in a periodic box."""
    fractions = plato.math.make_fractions(box, positions)
    thetas = 2*np.pi*fractions
    sums = np.sum(np.exp(1j*thetas), axis=0)
    fractions -= np.angle(sums)/2/np.pi + .5
    fractions -= target
    fractions %= 1.
    result = plato.math.fractions_to_coordinates(box, fractions)
    return np.ascontiguousarray(result)

def wrap(box, positions):
    fractions = plato.math.make_fractions(box, positions)
    fractions %= 1.
    return plato.math.fractions_to_coordinates(box, fractions)

@flowws.add_stage_arguments
class Center(flowws.Stage):
    """Center the system through periodic boundary conditions.

    This module modifies the positions of the system to have either
    the center of mass of the system or a single indicated particle at
    (0, 0, 0).
    """
    ARGS = [
        Arg('particle', '-p', int, -1,
            help='Particle index to center with (default: use center of mass of the system)'),
    ]

    def run(self, scope, storage):
        """Center the system."""
        box = scope.get('box', None)
        positions = scope['position']
        self.arg_specifications['particle'].valid_values = flowws.Range(
            -1, len(positions), (True, False))

        index = self.arguments['particle']
        index = index if index >= 0 else None

        if index is not None:
            center_point = positions[index]
            positions -= center_point[np.newaxis]

            if box is not None:
                positions = wrap(box, positions)

        elif box is None:
            center_point = np.mean(positions, axis=0)
            positions -= center_point[np.newaxis]

        else:
            positions = center(box, positions)

        scope['position'] = positions
