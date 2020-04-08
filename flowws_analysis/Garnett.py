import collections
import functools
import json
import os

import flowws
from flowws import Argument as Arg
import garnett
import numpy as np

GARNETT_READERS = dict(
    cif=garnett.reader.CifFileReader,
    dcd=garnett.reader.DCDFileReader,
    gsd=garnett.reader.GSDHoomdFileReader,
    pos=garnett.reader.PosFileReader,
    sqlite=garnett.reader.GetarFileReader,
    tar=garnett.reader.GetarFileReader,
    zip=garnett.reader.GetarFileReader,
)

GARNETT_TEXT_MODES = {'cif', 'pos'}

@flowws.add_stage_arguments
class Garnett(flowws.Stage):
    """Emit the contents of a :std:doc:`garnett<garnett:index>`-readable trajectory.

    The Garnett module outputs frames from a trajectory to be used for
    analysis and visualization.
    """
    ARGS = [
        Arg('filename', '-i', str, required=True,
            help='Filename to open'),
        Arg('frame', '-f', int, 0,
            help='Frame to load'),
        Arg('loop_frames', type=bool, default=False,
            help='If True, loop the workflow over frames found in the trajectory file, beginning at the given frame'),
    ]

    def __init__(self, *args, **kwargs):
        self._garnett_file = None
        self._looping = False
        super().__init__(*args, **kwargs)

    @functools.lru_cache(maxsize=1)
    def _get_traj(self, filename, storage):
        if self._garnett_file is not None:
            self._garnett_file.close()

        try:
            garnett_file = None

            suffix = os.path.splitext(self.arguments['filename'])[1][1:]
            reader = GARNETT_READERS[suffix]
            mode = 'r' if suffix in GARNETT_TEXT_MODES else 'rb'

            garnett_file = storage.open(
                self.arguments['filename'], mode, on_filesystem=True)
            garnett_traj = reader().read(garnett_file)

            self._garnett_file = garnett_file
            garnett_file = None
        finally:
            if garnett_file is not None:
                garnett_file.close()

        return garnett_traj

    def run(self, scope, storage):
        """Load records found in a getar file into the scope."""
        scope['filename'] = self.arguments['filename']
        scope['frame'] = self.arguments['frame']
        scope['cache_key'] = scope['filename'], scope['frame']

        garnett_traj = self._get_traj(self.arguments['filename'], storage)
        self.arg_specifications['frame'].valid_values = flowws.Range(
            0, len(garnett_traj), (True, False))
        frame = garnett_traj[self.arguments['frame']]

        # account for changes in the garnett API around v0.7
        try:
            types = frame.typeid
            positions = frame.position
            # account for some types of frames, like those from CIF
            # files, not exposing orientations and raising an
            # AttributeError instead
            try:
                orientations = frame.orientation
            except AttributeError:
                orientations = None
        except AttributeError:
            type_map = {k: i for (i, k) in enumerate(sorted(set(frame.types)))}
            types = np.array([type_map[t] for t in frame.types], dtype=np.uint32)
            positions = frame.positions
            try:
                orientations = frame.orientations
            except AttributeError:
                orientations = None

        try:
            type_shapes = [shape.type_shape for shape in frame.shapedef.values()]
            type_shapes = json.dumps(type_shapes)
            scope['type_shapes.json'] = type_shapes
        except AttributeError: # no shapedefs
            pass

        scope['position'] = positions
        if orientations is not None:
            scope['orientation'] = orientations
        scope['type'] = types
        scope['box'] = frame.box.get_box_array()
        scope['dimensions'] = frame.box.dimensions
