import collections
import flowws
from flowws import Argument as Arg
import garnett
import numpy as np

FakeFrame = collections.namedtuple(
    'FakeFrame', ['box', 'position', 'orientation', 'types', 'typeid'])

@flowws.add_stage_arguments
class SaveGarnett(flowws.Stage):
    """Save trajectory quantities using Garnett.

    This stage currently only saves an individual frame, but saving an
    entire trajectory is intended to work in the future.
    """
    ARGS = [
        Arg('filename', '-f', str, 'trajectory.sqlite',
            help='Name of file to save trajectory to'),
    ]

    def run(self, scope, storage):
        """Save trajectory quantities."""
        filename = self.arguments['filename']

        box = scope['box']
        box = garnett.trajectory.Box(
            Lx=box[0], Ly=box[1], Lz=box[2], xy=box[3], xz=box[4], yz=box[5])
        positions = scope['position']
        if 'orientation' in scope:
            orientations = scope['orientation']
        else:
            orientations = np.tile([(1, 0, 0, 0)], (len(positions), 1))
        types = scope['type']

        if 'type_names' not in scope:
            type_names = [chr(ord('A') + t) for t in sorted(set(types))]
        else:
            type_names = scope['type_names']

        the_frame = FakeFrame(box, positions, orientations, type_names, types)

        mode = ('w' if any(filename.endswith(suf) for suf in ['.pos', '.cif'])
                else 'wb')

        with storage.open(
                self.arguments['filename'], mode=mode, on_filesystem=True) as f:
            garnett.write([the_frame], f.name)
