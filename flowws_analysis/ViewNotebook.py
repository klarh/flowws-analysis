import argparse
import contextlib
import importlib
import functools

import flowws
from flowws import Argument as Arg
import IPython
import ipywidgets as ipw

_NON_LIVE_PLATO_BACKENDS = [
    'matplotlib',
    'povray',
    'pythreejs',
    'zdog',
]

@contextlib.contextmanager
def manage_matplotlib_interactive():
    import matplotlib.pyplot
    was_interactive = matplotlib.pyplot.isinteractive()
    matplotlib.pyplot.ioff()

    yield None
    if was_interactive:
        matplotlib.pyplot.ion()

@flowws.add_stage_arguments
class ViewNotebook(flowws.Stage):
    """Provide an interactive view of the entire workflow using jupyter widgets.

    Interactive widgets will be created inside the notebook. Arguments
    for each stage can be adjusted while viewing the visual results.
    """
    ARGS = [
        Arg('controls', '-c', bool, True,
            help='Display controls'),
        Arg('plato_backend', None, str, 'vispy',
            help='Plato backend to use for associated visuals'),
        Arg('vispy_backend', None, str,
            help='Vispy backend to use for plato visuals'),
    ]

    def __init__(self, *args, **kwargs):
        self.workflow = None
        self._visual_cache = {}
        self._output_cache = {}
        super().__init__(*args, **kwargs)

    def run(self, scope, storage):
        """Displays parameters and outputs for the workflow in an IPython notebook."""
        self._last_scope = scope
        self._last_storage = storage
        self._maybe_make_config(scope.setdefault('workflow', None))
        self.workflow = scope['workflow']
        self._display_outputs(scope.get('visuals', []))
        scope['visual_objects'] = self._visual_cache

        linked_visuals = [self._visual_cache[v] for v in
                          self._last_scope.get('visual_link_rotation', [])]
        for visual in linked_visuals:
            visual.enable('link_rotation', targets=linked_visuals)

        scope['rerun_callback'] = self.workflow.run

    def _display_outputs(self, visuals):
        for vis in visuals:
            if vis not in self._visual_cache:
                out = self._output_cache[vis] = ipw.Output()
                IPython.display.display(out)
            out = self._output_cache[vis]

            if hasattr(vis, 'draw_matplotlib'):
                import matplotlib.pyplot as pp
                import matplotlib
                if vis not in self._visual_cache:
                    self._visual_cache[vis] = matplotlib.figure.Figure()
                fig = self._visual_cache[vis]
                with out:
                    fig.clf()
                    vis.draw_matplotlib(fig)
                    fig.canvas.draw()
                    IPython.display.clear_output(wait=True)
                    IPython.display.display(fig)
            elif hasattr(vis, 'draw_plato'):
                if 'vispy_backend' in self.arguments:
                    import vispy.app
                    vispy.app.use_app(self.arguments['vispy_backend'])

                pkgname = 'plato.draw.{}'.format(self.arguments['plato_backend'])
                draw = importlib.import_module(pkgname)

                if self.arguments['plato_backend'] == 'vispy':
                    # work around a bug in vispy's show()
                    out = contextlib.nullcontext()
                elif self.arguments['plato_backend'] in _NON_LIVE_PLATO_BACKENDS:
                    # these don't update their contents in realtime, so always recreate
                    self._visual_cache.pop(vis, None)
                    with out:
                        IPython.display.clear_output(wait=True)

                basic_scene = vis.draw_plato()
                if vis not in self._visual_cache:
                    self._visual_cache[vis] = basic_scene.convert(draw, clip_scale=8)
                    with out:
                        if self.arguments['plato_backend'] == 'matplotlib':
                            import matplotlib, matplotlib.pyplot
                            dpi = matplotlib.rcParams['figure.dpi']
                            figsize = basic_scene.size_pixels/dpi
                            with manage_matplotlib_interactive():
                                fig = matplotlib.pyplot.figure(
                                    id(vis), figsize=figsize, dpi=dpi, clear=True)
                                (fig, _) = self._visual_cache[vis].render(fig)
                            IPython.display.display(fig)
                        else:
                            self._visual_cache[vis].show()
                vispy_scene = self._visual_cache[vis]

                should_clear = len(vispy_scene) != len(basic_scene)
                should_clear |= any(not isinstance(a, type(b)) for (a, b) in
                                    zip(vispy_scene, basic_scene))
                if should_clear:
                    for prim in reversed(list(vispy_scene)):
                        vispy_scene.remove_primitive(prim)
                    for prim in basic_scene.convert(draw):
                        vispy_scene.add_primitive(prim)
                else:
                    for (src, dest) in zip(basic_scene, vispy_scene):
                        dest.copy_from(src, True)

                for feature in (vispy_scene.enabled_features -
                                basic_scene.enabled_features):
                    vispy_scene.disable(feature)
                for feature in basic_scene.enabled_features:
                    config = basic_scene.get_feature_config(feature)
                    vispy_scene.enable(feature, **config)
                try:
                    if self.arguments['plato_backend'] != 'matplotlib':
                        vispy_scene.render()
                except AttributeError:
                    pass
            else:
                with out:
                    IPython.display.clear_output(wait=True)
                    IPython.display.display(vis)

    def _maybe_make_config(self, workflow):
        if self.workflow is not None or not self.arguments['controls']:
            return
        config_widgets = []

        for stage in workflow.stages:
            if stage is self:
                continue

            label = ipw.HTML('<center><b>{}</b></center>'.format(type(stage).__name__))
            stage_widgets = [label]
            for arg in stage.arg_specification_list:
                callback = functools.partial(self.rerun, arg, stage)

                if arg.type == int:
                    widget = ipw.IntSlider(description=arg.name)
                    if isinstance(arg.valid_values, flowws.Range):
                        widget.min = (arg.valid_values.min +
                                      (not arg.valid_values.inclusive[0]))
                        widget.max = (arg.valid_values.max -
                                      (not arg.valid_values.inclusive[1]))
                    if arg.name in stage.arguments:
                        widget.value = stage.arguments[arg.name]
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)
                elif arg.type == float:
                    widget = ipw.FloatSlider(description=arg.name)
                    if isinstance(arg.valid_values, flowws.Range):
                        delta = arg.valid_values.max - arg.valid_values.min
                        widget.min = (arg.valid_values.min +
                                      1e-2*delta*(not arg.valid_values.inclusive[0]))
                        widget.max = (arg.valid_values.max -
                                      1e-2*delta*(not arg.valid_values.inclusive[1]))
                    if arg.name in stage.arguments:
                        widget.value = stage.arguments[arg.name]
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)
                elif arg.type == str:
                    if arg.valid_values is not None:
                        widget = ipw.Dropdown(
                            description=arg.name, options=arg.valid_values)
                    else:
                        widget = ipw.Text(description=arg.name)
                    if arg.name in stage.arguments:
                        widget.value = stage.arguments[arg.name]
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)
                elif arg.type in (list, tuple):
                    if arg.valid_values is not None:
                        widget = ipw.Dropdown(
                            description=arg.name, value=stage.arguments[arg.name],
                            options=arg.valid_values)
                    else:
                        callback = functools.partial(
                            self.rerun, arg, stage, eval_first=True)
                        widget = ipw.Text(description=arg.name)
                        if arg.name in stage.arguments:
                            widget.value = str(stage.arguments[stage.name])
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)

            for (label, callback) in getattr(stage, 'gui_actions', []):
                widget = ipw.Button(description=label)
                widget.on_click(
                    lambda b, c=callback: c(self._last_scope, self._last_storage))
                stage_widgets.append(widget)

            stage_widget = ipw.VBox(stage_widgets)
            config_widgets.append(stage_widget)

        config_widget = ipw.GridBox(config_widgets)
        config_widget.layout = ipw.Layout(grid_template_columns="repeat(3, 33%)")
        IPython.display.display(config_widget)

    def rerun(self, arg, stage, change, eval_first=False):
        value = change['new']
        if eval_first:
            value = eval(value)

        stage.arguments[arg.name] = value

        if self.workflow is not None:
            self.workflow.run()
