import argparse
import functools

import flowws
from flowws import Argument as Arg
import matplotlib, matplotlib.cm
import numpy as np

@flowws.add_stage_arguments
class Colormap(flowws.Stage):
    """Access and use matplotlib colormaps on scalar quantities.

    This module emits a `color` value, calculated using a given scalar
    argument and matplotlib colormap name.

    Valid scalars quantities can be provided to this module by saving
    them in the scope and adding their name to the `color_scalars`
    list.
    """
    ARGS = [
        Arg('colormap_name', '-c', str, 'viridis',
            help='Name of the matplotlib colormap to use'),
        Arg('argument', '-a', str,
            help='Name of the value to map to colors'),
        Arg('range', '-r', (float, float),
            help='Minimum and maximum values of the scalar to be mapped'),
    ]

    def run(self, scope, storage):
        """Generate an array of colors using the given color scalars."""
        color_scalars = scope.setdefault('color_scalars', [])
        if 'type' not in color_scalars and 'type' in scope:
            color_scalars.append('type')

        self.arg_specifications['argument'].valid_values = color_scalars

        if self.arguments.get('argument', None) is None:
            self.arguments['argument'] = color_scalars[0]
        self.arg_specifications['colormap_name'].valid_values = \
            sorted(matplotlib.cm.cmap_d.keys())

        N = len(scope['position'])

        try:
            values = scope[self.arguments['argument']].copy()
        except KeyError:
            values = np.full(N, 0.5)

        normalize = None
        if self.arguments.get('range', None):
            (vmin, vmax) = self.arguments['range']
            normalize = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)

        cmap = matplotlib.cm.get_cmap(self.arguments['colormap_name'])
        smap = matplotlib.cm.ScalarMappable(normalize, cmap)

        scope['color'] = smap.to_rgba(values)
