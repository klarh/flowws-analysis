import flowws
from flowws import Argument as Arg
import pyriodic

VALID_STRUCTURES = []
for (name,) in pyriodic.db.query('select name from unit_cells'):
    VALID_STRUCTURES.append(name)

@flowws.add_stage_arguments
class Pyriodic(flowws.Stage):
    """Provide the contents of a getar-format file into the scope"""
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
        structure_name = self.arguments['structure']
        query = 'select structure from unit_cells where name = ? limit 1'
        for (structure,) in pyriodic.db.query(query, (structure_name,)):
            pass

        structure = structure.rescale_shortest_distance(1)
        structure = structure.replicate_upto(self.arguments['size'])
        if self.arguments['noise']:
            structure = structure.add_gaussian_noise(self.arguments['noise'])

        scope['position'] = structure.positions
        scope['type'] = structure.types
        scope['box'] = structure.box
