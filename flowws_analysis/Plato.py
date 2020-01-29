import json

import flowws
from flowws import Argument as Arg
import numpy as np
import plato, plato.draw as draw

PRIM_NAME_MAP = dict(
    sphere=draw.Spheres,
    disk=draw.Disks,
    convexpolyhedron=draw.ConvexPolyhedra,
    polygon=draw.Polygons,
    mesh=draw.Mesh,
)

TYPE_SHAPE_KWARG_MAP = {
    'rounding_radius': 'radius',
}

@flowws.add_stage_arguments
class Plato(flowws.Stage):
    """Render shapes via plato"""
    ARGS = [
    ]

    def run(self, scope, storage):
        """Prepare data for plato primitives"""
        positions = np.asarray(scope['position'])
        N = len(positions)
        if 'type' in scope:
            types = np.asarray(scope['type'])
        else:
            types = np.repeat(0, N)
        unique_types = list(sorted(set(types)))

        if 'type_shapes.json' in scope:
            type_shapes = json.loads(scope['type_shapes.json'])
        else:
            type_shapes = []

        if 'dimensions' in scope:
            dimensions = scope['dimensions']
        elif type_shapes and any(shape['name'].lower() in ('disk', 'polygon')
                                 for shape in type_shapes):
            dimensions = 2
        elif np.allclose(positions[:, 2], 0):
            dimensions = 2
        else:
            dimensions = 3

        orientations = np.atleast_2d(scope.get('orientation', []))
        if len(orientations) < N:
            orientations = np.tile([[1, 0, 0, 0.]], (N, 1))

        colors = np.atleast_2d(scope.get('color', []))
        if len(colors) < N:
            colors = np.tile([[.25, .55, .95, 1.]], (N, 1))

        diameters = np.atleast_1d(scope.get('diameter', 1))
        if len(diameters) < N:
            diameters = np.repeat(1, N)

        while len(type_shapes) < len(unique_types):
            if dimensions == 2:
                type_shapes.append(dict(name='Disk'))
            else:
                type_shapes.append(dict(name='Sphere'))

        primitives = []
        for (t, description) in zip(unique_types, type_shapes):
            filt = types == t

            prim_type = description['name'].lower()
            prim_class = PRIM_NAME_MAP[prim_type]

            if prim_type == 'convexpolyhedron' and description.get('rounding_radius', 0):
                prim_class = draw.ConvexSpheropolyhedra
            elif prim_type == 'polygon' and description.get('rounding_radius', 0):
                prim_class = draw.Spheropolygons

            kwargs = dict(description)
            kwargs.pop('name')
            for key in list(kwargs):
                new_key = TYPE_SHAPE_KWARG_MAP.get(key, key)
                kwargs[new_key] = kwargs.pop(key)
            prim = prim_class(**kwargs)

            prim.positions = positions[filt]
            prim.orientations = orientations[filt]
            prim.colors = colors[filt]
            prim.diameters = diameters[filt]

            primitives.append(prim)

        if 'box' in scope:
            prim = draw.Box.from_box(scope['box'])
            prim.width = min(scope['box'][:3])*1e-2
            prim.color = (0, 0, 0, 1)
            primitives.append(prim)

        self.scene = draw.Scene(primitives)

        scope.setdefault('visuals', []).append(self)

    def draw_plato(self):
        return self.scene
