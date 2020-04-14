import bisect
import functools

import flowws
from flowws import Argument as Arg
import gtar

gtar.widths.setdefault('color', 4)

def index_sort_key(x):
    """Sorting key to use for getar frame indices"""
    return (len(x), x)

def find_le(a, x):
    """Find rightmost value less than or equal to x"""
    i = bisect.bisect_right(a, x)
    if i:
        return a[i-1]
    raise ValueError

@flowws.add_stage_arguments
class GTAR(flowws.Stage):
    """Emit the contents of a :std:doc:`libgetar<libgetar:index>`-format file into the scope.

    The GTAR module outputs the records found in a getar-format file
    directly into the scope. It provides a notion of frames in a
    trajectory using the discretely-varying record with the most
    indices as the basis.
    """
    ARGS = [
        Arg('filename', '-i', str, required=True,
            help='Getar-format filename to open'),
        Arg('frame', '-f', int, 0,
            help='Frame to load'),
        Arg('loop_frames', type=bool, default=False,
            help='If True, loop the workflow over frames found in the trajectory file, beginning at the given frame'),
    ]

    def __init__(self, *args, **kwargs):
        self._cached_record_frames = {}
        self._gtar_traj = self._gtar_file = None
        self._looping = False
        super().__init__(*args, **kwargs)

    @functools.lru_cache(maxsize=1)
    def _get_traj(self, filename, storage):
        for handle in (self._gtar_traj, self._gtar_file):
            if handle is not None:
                handle.close()

        try:
            gtar_file = gtar_traj = None

            gtar_file = storage.open(
                self.arguments['filename'], 'rb', on_filesystem=True)
            gtar_traj = gtar.GTAR(gtar_file.name, 'r')

            self._gtar_file, self._gtar_traj = gtar_file, gtar_traj
            gtar_file = gtar_traj = None
        finally:
            for handle in (gtar_traj, gtar_file):
                if handle is not None:
                    handle.close()

        return self._gtar_traj

    def run(self, scope, storage):
        """Load records found in a getar file into the scope."""
        scope['filename'] = self.arguments['filename']
        scope['frame'] = self.arguments['frame']
        scope['cache_key'] = scope['filename'], scope['frame']

        gtar_traj = self._get_traj(self.arguments['filename'], storage)

        self._cache_record_frames(gtar_traj, scope, storage)
        if self.arguments['loop_frames'] and not self._looping:
            self._looping, self.arguments['loop_frames'] = True, False
            try:
                # loop over all frames except the last one
                frame_max = len(self._cached_frame_indices)
                frames = range(self.arguments['frame'], frame_max - 1)
                for frame in frames:
                    self.arguments['frame'] = frame
                    scope['workflow'].run()
            finally:
                self._looping, self.arguments['loop_frames'] = False, True
                # now run the last frame
                self.arguments['frame'] = max(0, len(self._cached_frame_indices) - 1)

        recs = self._set_record_frames()

        for rec in recs:
            callback = functools.partial(gtar_traj.getRecord, rec, rec.getIndex())
            scope.set_call(rec.getName(), callback)

    def _cache_record_frames(self, traj, scope, storage):
        self._cached_record_frames = {}
        for rec in traj.getRecordTypes():
            # ignore per-bond records and so on, for now
            if rec.getGroup() != '':
                continue

            self._cached_record_frames[rec] = list(map(
                index_sort_key, traj.queryFrames(rec)))

        (_, self._cached_frame_indices) = max(
            (len(indices), indices) for (rec, indices) in
            self._cached_record_frames.items() if
            rec.getBehavior() == gtar.Behavior.Discrete)

    def _set_record_frames(self):
        frame = self.arguments['frame']

        index_to_find = index_sort_key(self._cached_frame_indices[self.arguments['frame']][1])
        self.arg_specifications['frame'].valid_values = flowws.Range(
            0, len(self._cached_frame_indices), (True, False))

        for (rec, indices) in self._cached_record_frames.items():
            try:
                index = find_le(indices, index_to_find)[1]
                rec.setIndex(index)
            except ValueError:
                pass

        return self._cached_record_frames.keys()
