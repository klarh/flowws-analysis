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

SCENE_FEATURE_REMAP = {
    'additive_rendering': 'additive_rendering',
    'ambient_occlusion': 'ssao',
    'fast_antialiasing': 'fxaa',
}

@flowws.add_stage_arguments
class Plato(flowws.Stage):
    """Render shapes via plato.

    This module uses the `position`, `orientation`, `type`, `color`,
    and `type_shapes.json` quantities found in the scope, if provided,
    to produce a scene of `plato` shapes.

    The `type_shapes.json` value should provide a string of a
    json-encoded list containing one *shape description* object
    (described below) for each type. These will be converted into
    plato primitives in conjunction with the `type` and other arrays.

    Shape description objects are JSON objects with the following keys:

    - type: one of "ConvexPolyhedron", "Disk", "Mesh", "Polygon", "Sphere"
    - rounding_radius (only if type is "ConvexPolyhedron" or "Polygon"): rounding radius of a rounded shape, or 0 for perfectly faceted shapes
    - vertices (only if type is "ConvexPolyhedron", "Mesh", or "Polygon"): coordinates in the shape's reference frame for its vertices; 2D for polygon and 3D for other shapes
    - indices (only if type is "Mesh"): Array of triangle indices associated with the given set of vertices
    """
    ARGS = [
        Arg('outline', '-o', float, 0,
            help='Outline for all shapes'),
        Arg('color_scale', None, float, 1, valid_values=flowws.Range(0, 10, True),
            help='Factor to scale color RGB intensities by'),
        Arg('additive_rendering', None, bool, False,
            help='Use additive rendering for shapes'),
        Arg('fast_antialiasing', None, bool, False,
            help='Use Fast Approximate Antialiasing (FXAA)'),
        Arg('ambient_occlusion', None, bool, False,
            help='Use Screen Space Ambient Occlusion (SSAO)'),
        Arg('disable_rounding', None, bool, False,
            help='Disable spheropolyhedra and spheropolygons'),
    ]

    def run(self, scope, storage):
        """Generate a scene of plato primitives."""
        scene_kwargs = {}
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
            try:
                dimensions = dimensions[0]
            except TypeError:
                pass
        elif type_shapes and any(shape['type'].lower() in ('disk', 'polygon')
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
            colors = np.empty((N, 4), dtype=np.float32)
            colors[:, :3] = plato.cmap.cubeellipse_intensity(
                types.astype(np.float32), h=1.2, s=-0.25, lam=.45)
            colors[:, 3] = 1

        colors[:, :3] *= self.arguments['color_scale']

        diameters = np.atleast_1d(scope.get('diameter', 1))
        if len(diameters) < N:
            diameters = np.repeat(1, N)

        if self.arguments.get('disable_rounding', False):
            for description in type_shapes:
                if 'rounding_radius' in description:
                    description['rounding_radius'] = 0

        while len(type_shapes) < len(unique_types):
            if dimensions == 2:
                type_shapes.append(dict(type='Disk'))
            else:
                type_shapes.append(dict(type='Sphere'))

        primitives = []
        for (t, description) in zip(unique_types, type_shapes):
            filt = types == t

            prim_type = description['type'].lower()
            is_2d = prim_type in ('disk', 'polygon')
            prim_class = PRIM_NAME_MAP[prim_type]

            if prim_type == 'convexpolyhedron' and description.get('rounding_radius', 0):
                prim_class = draw.ConvexSpheropolyhedra
            elif prim_type == 'polygon' and description.get('rounding_radius', 0):
                prim_class = draw.Spheropolygons

            kwargs = dict(description)
            kwargs.pop('type')
            for key in list(kwargs):
                new_key = TYPE_SHAPE_KWARG_MAP.get(key, key)
                kwargs[new_key] = kwargs.pop(key)
            prim = prim_class(**kwargs)

            if is_2d:
                prim.positions = positions[filt, :2]
            else:
                prim.positions = positions[filt]
            prim.orientations = orientations[filt]
            prim.colors = colors[filt]
            prim.diameters = diameters[filt]
            prim.outline = self.arguments['outline']

            primitives.append(prim)

        if 'box' in scope:
            prim = draw.Box.from_box(scope['box'])
            prim.width = min(scope['box'][:dimensions])*5e-3
            prim.color = (0, 0, 0, 1)
            primitives.append(prim)

            scene_kwargs['size'] = 1.05*np.array(scope['box'][:2])
            # use default size of 800px wide
            scene_kwargs['pixel_scale'] = 800/scene_kwargs['size'][0]

        self.scene = draw.Scene(primitives, **scene_kwargs)

        if dimensions == 2:
            self.scene.enable('pan')

        for (argument_name, feature_name) in SCENE_FEATURE_REMAP.items():
            if self.arguments[argument_name]:
                self.scene.enable(feature_name)

        scope.setdefault('visuals', []).append(self)

    def draw_plato(self):
        return self.scene
