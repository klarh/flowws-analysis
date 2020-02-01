import argparse
import functools

import flowws
from flowws import Argument as Arg
import matplotlib, matplotlib.cm
import numpy as np

@flowws.add_stage_arguments
class Colormap(flowws.Stage):
    """Access and use matplotlib colormaps"""
    ARGS = [
        Arg('colormap_name', '-c', str, 'viridis',
            help='Name of the matplotlib colormap to use'),
        Arg('argument', '-a', str,
            help='Name of the value to map to colors'),
        Arg('range', '-r', (float, float),
            help='Minimum and maximum values of the scalar to be mapped'),
    ]

    def run(self, scope, storage):
        """Generate colors"""
        if 'color_scalars' in scope:
            self.arg_specifications['argument'].valid_values = scope['color_scalars']

            if self.arguments.get('argument', None) is None:
                self.arguments['argument'] = scope['color_scalars'][0]
        self.arg_specifications['colormap_name'].valid_values = \
            sorted(matplotlib.cm.cmap_d.keys())

        N = len(scope['position'])

        try:
            values = scope[self.arguments['argument']].copy()
        except KeyError:
            values = np.full(len(N), 0.5)

        normalize = None
        if self.arguments.get('range', None):
            (vmin, vmax) = self.arguments['range']
            normalize = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)

        cmap = matplotlib.cm.get_cmap(self.arguments['colormap_name'])
        smap = matplotlib.cm.ScalarMappable(normalize, cmap)

        scope['color'] = smap.to_rgba(values)
