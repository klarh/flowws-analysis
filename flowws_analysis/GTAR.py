import bisect
import functools

import flowws
from flowws import Argument as Arg
import gtar

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
    """Emit the contents of a getar-format file into the scope.

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
    ]

    def __init__(self, *args, **kwargs):
        self._cached_record_frames = {}
        self._cached_file_handles = None
        super().__init__(*args, **kwargs)

    def run(self, scope, storage):
        """Load records found in a getar file into the scope."""
        scope['filename'] = self.arguments['filename']
        scope['frame'] = self.arguments['frame']

        try:
            gtar_file = gtar_traj = None
            gtar_file = storage.open(
                self.arguments['filename'], 'rb', on_filesystem=True)
            gtar_traj = gtar.GTAR(gtar_file.name, 'r')

            if self._cached_file_handles:
                for v in reversed(self._cached_file_handles):
                    v.close()
            self._cached_file_handles = (gtar_file, gtar_traj)
        except:
            for handle in (gtar_traj, gtar_file):
                if handle is not None:
                    handle.close()

        self._cache_record_frames(gtar_traj, scope, storage)
        recs = self._set_record_frames()

        for rec in recs:
            callback = functools.partial(gtar_traj.getRecord, rec, rec.getIndex())
            scope.set_call(rec.getName(), callback)

    def _cache_record_frames(self, traj, scope, storage):
        self._cached_record_frames = {}
        for rec in traj.getRecordTypes():
            self._cached_record_frames[rec] = list(map(
                index_sort_key, traj.queryFrames(rec)))

    def _set_record_frames(self):
        frame = self.arguments['frame']

        (_, largest_indices) = max(
            (len(indices), indices) for (rec, indices) in
            self._cached_record_frames.items() if
            rec.getBehavior() == gtar.Behavior.Discrete)
        index_to_find = index_sort_key(largest_indices[self.arguments['frame']][1])
        self.arg_specifications['frame'].valid_values = flowws.Range(
            0, len(largest_indices), (True, False))

        for (rec, indices) in self._cached_record_frames.items():
            try:
                index = find_le(indices, index_to_find)[1]
                rec.setIndex(index)
            except ValueError:
                pass

        return self._cached_record_frames.keys()
