import argparse
import functools
import importlib

import flowws
from flowws import Argument as Arg

from .Plato import Plato

@flowws.add_stage_arguments
class Save(flowws.Stage):
    """Save all visuals created to individual files."""
    ARGS = [
        Arg('matplotlib_format', None, str, 'pdf',
            help='Format to save matplotlib figures in'),
        Arg('matplotlib_figure_kwargs', None, [(str, eval)],
            help='Additional keyword arguments to pass to matplotlib Figure creation'),
        Arg('plato_format', None, str, 'png',
            help='Format to save plato figures in'),
        Arg('plato_backend', None, str, 'vispy',
            help='Plato backend to use for associated visuals'),
        Arg('vispy_backend', None, str,
            help='Vispy backend to use for plato visuals'),
        Arg('file_modifiers', '-f', [str], [],
            help='List of additional filename modifiers to use'),
    ]

    def run(self, scope, storage):
        """Save all visuals found"""
        self._used_filenames = scope.setdefault('used_filenames', set())
        visuals = scope.get('visuals', [])

        for vis in visuals:
            if hasattr(vis, 'draw_matplotlib'):
                import matplotlib.pyplot as pp
                import matplotlib

                filename = 'output.{}'.format(self.arguments['matplotlib_format'])
                fig_kwargs = self.arguments.get('matplotlib_figure_kwargs', [])
                fig = matplotlib.figure.Figure(**dict(fig_kwargs))
                vis.draw_matplotlib(fig)

                modifiers = []
                if isinstance(vis, flowws.Stage):
                    modifiers.append(type(vis).__name__)
                modifiers.extend(self.arguments.get('file_modifiers', []))
                self._update_modifiers(filename, modifiers)

                with storage.open(filename, 'wb', modifiers) as f:
                    fig.savefig(f, format=self.arguments['matplotlib_format'])

            elif hasattr(vis, 'draw_plato'):
                kwargs = {}
                if 'vispy_backend' in self.arguments:
                    import vispy.app
                    vispy.app.use_app(self.arguments['vispy_backend'])

                    last_plato_visual = None
                    for vis in scope.get('visuals', []):
                        if isinstance(vis, Plato):
                            last_plato_visual = vis

                    plato_scene = scope.get('visual_objects', {}).get(last_plato_visual, None)

                    if plato_scene is not None:
                        kwargs['canvas_kwargs'] = dict(shared=plato_scene._canvas.context)

                pkgname = 'plato.draw.{}'.format(self.arguments['plato_backend'])
                draw = importlib.import_module(pkgname)

                filename = 'output.{}'.format(self.arguments['plato_format'])
                basic_scene = vis.draw_plato()
                backend_scene = basic_scene.convert(draw)

                modifiers = []
                if isinstance(vis, flowws.Stage):
                    modifiers.append(type(vis).__name__)
                modifiers.extend(self.arguments.get('file_modifiers', []))
                self._update_modifiers(filename, modifiers)

                if self.arguments['plato_backend'] == 'vispy':
                    backend_scene.show()

                with storage.open(filename, 'wb', modifiers, True) as f:
                    backend_scene.save(f.name)
            else:
                pass

    def _update_modifiers(self, filename, modifiers):
        key = (filename, tuple(modifiers))
        if key not in self._used_filenames:
            self._used_filenames.add(key)
            return

        i = 1
        modifiers.append('placeholder') # should be overwritten immediately
        while key in self._used_filenames:
            i += 1
            modifiers[-1] = str(i)
            key = (filename, tuple(modifiers))
