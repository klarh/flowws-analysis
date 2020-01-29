import argparse
import functools

import flowws
from flowws import Argument as Arg
import IPython
import ipywidgets as ipw

@flowws.add_stage_arguments
class ViewNotebook(flowws.Stage):
    """Provide a notebook-interactive view of the entire workflow"""
    ARGS = [
        Arg('controls', '-c', bool, True,
            help='Display controls'),
    ]

    def __init__(self, *args, **kwargs):
        self.workflow = None
        self._visual_cache = {}
        self._output_cache = {}
        super().__init__(*args, **kwargs)

    def run(self, scope, storage):
        """Displays parameters and outputs for the workflow in an IPython notebook"""
        self._maybe_make_config(scope.setdefault('workflow', None))
        self.workflow = scope['workflow']
        self._display_outputs(scope.get('visuals', []))

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
                import plato.draw.vispy as draw
                basic_scene = vis.draw_plato()
                if vis not in self._visual_cache:
                    self._visual_cache[vis] = basic_scene.convert(draw)
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

                vispy_scene.render()
            else:
                with out:
                    IPython.display.clear_output(wait=True)
                    IPython.display.display(vis)

        visuals.clear()

    def _maybe_make_config(self, workflow):
        if self.workflow is not None or not self.arguments['controls']:
            return
        config_widgets = []

        for stage in workflow.stages:
            if stage is self:
                continue

            label = ipw.HTML('<center><b>{}</b></center>'.format(type(stage).__name__))
            stage_widgets = [label]
            for arg in stage.ARGS:
                callback = functools.partial(self.rerun, arg, stage)

                if arg.type == int:
                    widget = ipw.IntSlider(
                        description=arg.name, value=stage.arguments[arg.name])
                    if isinstance(arg.valid_values, flowws.Range):
                        widget.min = (arg.valid_values.min +
                                      (not arg.valid_values.inclusive[0]))
                        widget.max = (arg.valid_values.max -
                                      (not arg.valid_values.inclusive[1]))
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)
                elif arg.type == float:
                    widget = ipw.FloatSlider(
                        description=arg.name, value=stage.arguments[arg.name])
                    if isinstance(arg.valid_values, flowws.Range):
                        delta = arg.valid_values.max - arg.valid_values.min
                        widget.min = (arg.valid_values.min +
                                      1e-2*delta*(not arg.valid_values.inclusive[0]))
                        widget.max = (arg.valid_values.max -
                                      1e-2*delta*(not arg.valid_values.inclusive[1]))
                    widget.observe(callback, names='value')
                    stage_widgets.append(widget)
                elif arg.type in (list, float, tuple):
                    if arg.valid_values is not None:
                        widget = ipw.Dropdown(
                            description=arg.name, value=stage.arguments[arg.name],
                            options=arg.valid_values)
                    else:
                        callback = functools.partial(
                            self.rerun, arg, stage, eval_first=True)
                        widget = ipw.Text(
                            description=arg.name, value=stage.arguments[arg.name])
                    widget.observe(callback, names='value')
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
