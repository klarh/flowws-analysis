
import argparse
import contextlib
import importlib
import logging
import functools
import threading
import traceback
import queue

import flowws
from flowws import Argument as Arg
from Qt import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)

class ViewQtWindow(QtWidgets.QMainWindow):
    def __init__(self, exit_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exit_event = exit_event

    def closeEvent(self, event):
        self._exit_event.set()

class ViewQtApp(QtWidgets.QApplication):
    def __init__(self, scope, workflow, rerun_event, stage_event, exit_event,
                 visual_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope = scope
        self.workflow = workflow
        self.rerun_event = rerun_event
        self.stage_event = stage_event
        self.exit_event = exit_event
        self.visual_queue = visual_queue

        self._visual_cache = {}

        self._make_widgets()
        self._make_timers()

    def _make_timers(self):
        self.stage_timer = QtCore.QTimer(self)
        self.stage_timer.timeout.connect(self._update_stage_config)
        self.stage_timer.start(1)

        self.visual_timer = QtCore.QTimer(self)
        self.visual_timer.timeout.connect(self._update_visuals)
        self.visual_timer.start(1)

        self.close_timer = QtCore.QTimer(self);
        self.close_timer.timeout.connect(self._check_close)
        self.close_timer.start(1)

    def _check_close(self):
        if self.exit_event.is_set():
            self.main_window.close()

    def _update_stage_config(self):
        if not self.stage_event.is_set():
            return

        self.stage_event.clear()
        # TODO cache some of these things instead of constantly recreating
        self._make_config_widgets()

    def _update_visuals(self):
        visuals = []
        try:
            while True:
                visuals = self.visual_queue.get_nowait()
        except queue.Empty: # skip to most recent visuals to display
            pass

        for vis in visuals:
            self._update_visual(vis)

    def _make_widgets(self):
        self.main_window = ViewQtWindow(self.exit_event)
        self.mdi_area = QtWidgets.QMdiArea(self.main_window)
        self.config_dock = QtWidgets.QDockWidget('Options', self.main_window)
        self.config_widget = QtWidgets.QFrame(self.config_dock)
        self.config_dock.setWidget(self.config_widget)

        self.main_window.setCentralWidget(self.mdi_area)
        self.main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.config_dock)

        self._make_config_widgets()
        self._make_visuals()

        self.main_window.show()

    def _make_config_widgets(self):
        widgets = []
        for stage in self.workflow.stages:
            groupbox = QtWidgets.QGroupBox(type(stage).__name__)
            layout = QtWidgets.QFormLayout()
            groupbox.setLayout(layout)

            for arg in stage.arg_specification_list:
                widget = self._make_config_widget(arg, stage)
                if widget is None:
                    continue

                layout.addRow(arg.name, widget)

            if layout.rowCount():
                widgets.append(groupbox)

        layout = QtWidgets.QVBoxLayout()
        for widget in widgets:
            layout.addWidget(widget)
        self.config_widget.setLayout(layout)

    def _make_config_widget(self, arg, stage):
        callback = functools.partial(self._rerun, arg, stage)
        result = None

        if arg.type == int:
            result = QtWidgets.QSpinBox()
            if arg.name in stage.arguments:
                val = stage.arguments[arg.name]
            else:
                val = result.value()

            if arg.valid_values is not None:
                range_ = arg.valid_values
            else:
                range_ = flowws.Range(0, val*4, True)

            result.setMinimum(range_.min +
                              (not range_.inclusive[0]))
            result.setMaximum(range_.max -
                              (not range_.inclusive[1]))
            result.setValue(val)
            result.valueChanged[int].connect(callback)
        elif arg.type == float:
            result = QtWidgets.QDoubleSpinBox()
            if arg.name in stage.arguments:
                val = stage.arguments[arg.name]
            else:
                val = 1

            if arg.valid_values is not None:
                range_ = arg.valid_values
            else:
                range_ = flowws.Range(0, val*4, True)

            delta = range_.max - range_.min
            result.setMinimum(range_.min +
                              1e-2*delta*(not range_.inclusive[0]))
            result.setMaximum(range_.max -
                              1e-2*delta*(not range_.inclusive[1]))
            result.setValue(val)
            result.valueChanged[float].connect(callback)
        elif arg.type == str:
            if arg.valid_values is not None:
                result = QtWidgets.QComboBox()
                result.addItems(arg.valid_values)
                if arg.name in stage.arguments:
                    result.setCurrentText(stage.arguments[arg.name])
                result.currentIndexChanged[str].connect(callback)
            else:
                result = QtWidgets.QLineEdit()
                if arg.name in stage.arguments:
                    result.setText(stage.arguments[arg.name])
                result.textChanged[str].connect(callback)

        return result

    def _rerun(self, arg, stage, value, eval_first=False):
        if eval_first:
            value = eval(value)

        stage.arguments[arg.name] = value

        self.rerun_event.set()

    def _make_visuals(self):
        visuals = list(self.scope.get('visuals', []))

        for vis in visuals:
            self._update_visual(vis)

        self.mdi_area.tileSubWindows()

    def _update_visual(self, vis):
        if hasattr(vis, 'draw_matplotlib'):
            from matplotlib.backends.backend_qt5agg import FigureCanvas
            from matplotlib.figure import Figure

            if vis not in self._visual_cache:
                fig = self._visual_cache[vis] = Figure(dpi=72)
                canvas = FigureCanvas(fig)
                self.mdi_area.addSubWindow(canvas)

            fig = self._visual_cache[vis]
            fig.clear()
            vis.draw_matplotlib(fig)
            fig.canvas.draw_idle()

        elif hasattr(vis, 'draw_plato'):
            import vispy, vispy.app
            vispy.app.use_app('PySide2')
            import plato.draw.vispy as draw
            basic_scene = vis.draw_plato()

            if vis not in self._visual_cache:
                scene = self._visual_cache[vis] = basic_scene.convert(draw)
                self.mdi_area.addSubWindow(scene._canvas.native)

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

            try:
                vispy_scene.render()
            except AttributeError:
                pass

class GuiThread(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args = kwargs['args']

    def run(self):
        (scope, workflow, rerun_event, stage_event, exit_event, visual_queue) = \
            self.args

        app = ViewQtApp(scope, workflow, rerun_event, stage_event, exit_event,
                        visual_queue, [])
        app.exec_()

@flowws.add_stage_arguments
class ViewQt(flowws.Stage):
    """Provide an interactive view of the entire workflow using Qt"""
    ARGS = [
        Arg('controls', '-c', bool, True,
            help='Display controls'),
    ]

    def __init__(self, *args, **kwargs):
        self.workflow = None
        self._running_threads = None
        self._rerun_event = threading.Event()
        self._stage_event = threading.Event()
        self._exit_event = threading.Event()
        self._visual_queue = queue.Queue()
        super().__init__(*args, **kwargs)

    def run(self, scope, storage):
        """Displays parameters and outputs for the workflow in an IPython notebook"""
        self.workflow = scope['workflow']

        if self._running_threads is None:
            args = (scope, self.workflow, self._rerun_event,
                    self._stage_event, self._exit_event, self._visual_queue)
            self._running_threads = gui_thread = GuiThread(args=args)
            gui_thread.start()

            while True:
                try:
                    self._rerun_event.wait(1e-2)
                    if self._rerun_event.is_set():
                        self._rerun_event.clear()
                        self.workflow.run()
                        self._stage_event.set()
                        self._visual_queue.put(scope.get('visuals', []))
                except KeyboardInterrupt:
                    self._exit_event.set()
                except Exception as e:
                    msg = traceback.format_exc(3)
                    logger.error(msg)

                if self._exit_event.is_set():
                    break

            gui_thread.join()
