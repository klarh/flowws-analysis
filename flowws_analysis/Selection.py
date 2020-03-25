import functools

import flowws
from flowws import Argument as Arg
import plato
import numpy as np

DEFAULT_PARTICLE_QUANTITIES = [
    'color',
    'orientation',
    'position',
    'type',
]

def mouse_selection_callback(start_point, end_point, selection_module, scope, scene):
    lowers = np.min([start_point, end_point], axis=0)
    uppers = np.max([start_point, end_point], axis=0)
    selection_module._add_mouse_selection(
        scope, scene.rotation, scene.translation, lowers, uppers)

@flowws.add_stage_arguments
class Selection(flowws.Stage):
    """Filter the set of displayed particles manually or by specified criteria.

    This module removes particles by filtering all per-particle
    quantities according to a series of criteria, such as
    `potential_energy < -0.5`.

    When used interactively with vispy scenes, selections can be made
    with the mouse, or particles on the convex hull of a droplet can
    be removed.

    """
    ARGS = [
        Arg('criteria', None, [str], [],
            help='List of criteria to filter by. Particles satisfying all criteria will be included.'),
    ]

    def run(self, scope, storage):
        """Evaluate the given selection criteria and filter particles."""
        found_quantities = [name for name in DEFAULT_PARTICLE_QUANTITIES
                                 if name in scope]

        namespace = dict(scope)
        namespace['numpy'] = namespace['np'] = np

        for criterion in self.arguments['criteria']:
            this_filter = eval(criterion, namespace)

            for name in found_quantities:
                scope[name] = scope[name][this_filter]

        self.gui_actions = [
            ('Select rectangle', self._rectangle_callback),
            ('Undo last selection', self._pop_selection),
            ('Remove convex hull', self._remove_hull),
        ]

    def _rectangle_callback(self, scope, storage):
        visual_target = scope['selection_visual_target']
        plato_scene = scope['visual_objects'][visual_target]

        mouse_callback = functools.partial(
            mouse_selection_callback, selection_module=self, scope=scope,
            scene=plato_scene)
        plato_scene.enable('select_rect', mouse_callback)

    def _pop_selection(self, scope, storage):
        if self.arguments['criteria']:
            self.arguments['criteria'].pop()

        if scope.get('rerun_callback', None) is not None:
            scope['rerun_callback']()

    def _remove_hull(self, scope, storage):
        from .Center import center
        from scipy.spatial import ConvexHull

        positions = scope['position']
        box = scope['box']

        positions = center(box, positions)
        hull = ConvexHull(positions)
        hull_indices = set(hull.vertices)
        keep_indices = [i for i in range(len(positions)) if i not in hull_indices]

        self.arguments['criteria'].append(str(keep_indices))

        if scope.get('rerun_callback', None) is not None:
            scope['rerun_callback']()

    def _add_mouse_selection(self, scope, rotation, translation, lower, upper):
        positions = plato.math.quatrot(rotation, scope['position'])
        positions += translation

        above = np.all(positions[:, :2] > lower, axis=-1)
        below = np.all(positions[:, :2] < upper, axis=-1)

        inside = np.logical_and(above, below)
        indices = np.where(inside)[0]

        if len(indices):
            self.arguments['criteria'].append(str(indices.tolist()))

            if scope.get('rerun_callback', None) is not None:
                scope['rerun_callback']()
