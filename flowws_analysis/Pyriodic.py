import functools

import flowws
from flowws import Argument as Arg
import pyriodic

VALID_STRUCTURES = []
for (name,) in pyriodic.db.query('select distinct name from unit_cells order by name'):
    VALID_STRUCTURES.append(name)

@flowws.add_stage_arguments
class Pyriodic(flowws.Stage):
    """Browse structures available in :std:doc:`pyriodic<pyriodic:index>`.

    This module provides all the structures available in the pyriodic
    default database (which uses all available pyriodic libraries
    installed on the system). Systems are resized to a minimum of the
    given size and noise may be added before the rest of the workflow
    is run.
    """
    ARGS = [
        Arg('structure', '-s', str, required=True,
            valid_values=VALID_STRUCTURES,
            help='Structure to display'),
        Arg('size', '-n', int, default=1,
            help='Minimum size of the system'),
        Arg('noise', None, float, default=0,
            help='Gaussian noise to apply to each position'),
    ]

    def run(self, scope, storage):
        """Load the given structure into the scope"""
        structure = self._get_structure(
            self.arguments['structure'], self.arguments['size'],
            self.arguments['noise'])

        scope['position'] = structure.positions
        scope['type'] = structure.types
        scope['box'] = structure.box

    @functools.lru_cache(maxsize=1)
    def _get_structure(self, name, size, noise):
        query = 'select structure from unit_cells where name = ? limit 1'
        for (structure,) in pyriodic.db.query(query, (name,)):
            pass

        structure = structure.rescale_shortest_distance(1)
        structure = structure.replicate_upto(size)
        if noise:
            structure = structure.add_gaussian_noise(self.arguments['noise'])

        return structure
