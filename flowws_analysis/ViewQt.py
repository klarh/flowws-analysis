
import argparse
import contextlib
import functools
import hashlib
import importlib
import json
import logging
import os
import signal
import threading
import traceback
import queue

import flowws
from flowws import Argument as Arg
import Qt
from Qt import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)

def _bool_checkbox_helper(f):
    remap = {
        QtCore.Qt.CheckState.Checked: True,
        QtCore.Qt.CheckState.Unchecked: False
    }
    def result(value):
        return f(remap[value])
    return result

class ViewQtWindow(QtWidgets.QMainWindow):
    def __init__(self, exit_event, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._exit_event = exit_event
        self._settings_keys = 'None', 'None'

    def _load_state(self):
        settings = QtCore.QSettings('flowws-analysis', 'ViewQt')
        for key_id in self._settings_keys:
            state_key = 'autosave/{}/window_state'.format(key_id)
            state = settings.value(state_key, None)
            geom_key = 'autosave/{}/geometry'.format(key_id)
            geom = settings.value(geom_key)

            if state is not None:
                self.restoreState(state)
                self.restoreGeometry(geom)

                iterations = enumerate(self.centralWidget().subWindowList())
                for (i, window) in iterations:
                    geom_key = 'autosave/{}/{}/geometry'.format(key_id, i)
                    window_geom = settings.value(geom_key, None)
                    if window_geom is not None:
                        window.setGeometry(window_geom)

                return

    def _save_state(self):
        settings = QtCore.QSettings('flowws-analysis', 'ViewQt')
        state = self.saveState()
        geom = self.saveGeometry()

        for key_id in self._settings_keys:
            state_key = 'autosave/{}/window_state'.format(key_id)
            settings.setValue(state_key, state)
            geom_key = 'autosave/{}/geometry'.format(key_id)
            settings.setValue(geom_key, geom)

            for (i, window) in enumerate(self.centralWidget().subWindowList()):
                geom_key = 'autosave/{}/{}/geometry'.format(key_id, i)
                settings.setValue(geom_key, window.geometry())

    def _setup_state(self, stages, visuals):
        stage_names = [type(stage).__name__ for stage in stages]
        vis_names = [type(vis).__name__ for vis in visuals]

        vis_hash = hashlib.sha1(b'flowws-analysis.ViewQt')
        vis_hash.update(b'vis_names')
        vis_hash.update(';'.join(vis_names).encode())

        full_hash = vis_hash.copy()
        full_hash.update(b'stage_names')
        full_hash.update(';'.join(stage_names).encode())

        self._settings_keys = full_hash.hexdigest()[:32], vis_hash.hexdigest()[:32]

    def closeEvent(self, event):
        self._save_state()
        self._exit_event.set()
        super().closeEvent(event)

class ViewQtApp(QtWidgets.QApplication):
    def __init__(self, workflow, rerun_event, stage_event, exit_event,
                 visual_queue, display_controls, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.workflow = workflow
        self.rerun_event = rerun_event
        self.stage_event = stage_event
        self.exit_event = exit_event
        self.visual_queue = visual_queue

        self._visual_cache = {}
        self._currently_refreshing = False

        self._make_widgets(display_controls)
        self._make_menu()
        self._make_timers()

    def _check_close(self):
        if self.exit_event.is_set():
            self.main_window.close()

    def _make_config_widget(self, arg, stage):
        callback = functools.partial(self._rerun, arg, stage)
        result = None

        if arg.type == int:
            result = QtWidgets.QSpinBox()
            if arg.name in stage.arguments:
                val = stage.arguments[arg.name]
            else:
                val = 0

            if arg.valid_values is not None:
                range_ = arg.valid_values
                result.setMinimum(range_.min +
                                  (not range_.inclusive[0]))
                result.setMaximum(range_.max -
                                  (not range_.inclusive[1]))
            else:
                result.setMaximum(max(1024, val*4))
            result.setValue(val)
            result.valueChanged[int].connect(callback)
        elif arg.type == float:
            result = QtWidgets.QDoubleSpinBox()
            if arg.name in stage.arguments:
                val = stage.arguments[arg.name]
            else:
                val = 0

            if arg.valid_values is not None:
                range_ = arg.valid_values
            else:
                range_ = flowws.Range(0, val*4 if val else 8, True)

            delta = range_.max - range_.min

            result.setMinimum(range_.min +
                              1e-2*delta*(not range_.inclusive[0]))
            result.setMaximum(range_.max -
                              1e-2*delta*(not range_.inclusive[1]))
            result.setSingleStep(5e-2*delta)
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
        elif arg.type == bool:
            result = QtWidgets.QCheckBox()
            if arg.name in stage.arguments:
                result.setChecked(stage.arguments[arg.name])
            result.stateChanged.connect(_bool_checkbox_helper(callback))

        return result

    def _make_config_widgets(self):
        widgets = []
        for stage in self.workflow.stages:
            if isinstance(stage, ViewQt):
                continue
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

    def _make_menu(self):
        self.menubar = QtWidgets.QMenuBar()

        self.file_menu = self.menubar.addMenu('&File')
        save_action = self.file_menu.addAction('&Save')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self._save_json)
        self.file_menu.addAction(save_action)
        close_action = self.file_menu.addAction('&Close')
        close_action.setShortcut('Ctrl+W')
        close_action.triggered.connect(lambda *args: self.main_window.close())
        self.file_menu.addAction(close_action)

        self.view_menu = self.menubar.addMenu('&View')
        self.view_menu.addSection('Windows')
        tile_action = self.view_menu.addAction('&Tile')
        tile_action.triggered.connect(
            lambda *args: self.mdi_area.tileSubWindows())
        self.view_menu.addAction(tile_action)
        cascade_action = self.view_menu.addAction('&Cascade')
        cascade_action.triggered.connect(
            lambda *args: self.mdi_area.cascadeSubWindows())
        self.view_menu.addAction(cascade_action)
        refresh_action = self.view_menu.addAction('&Refresh')
        refresh_action.setShortcut('Ctrl+R')
        refresh_action.triggered.connect(self._refresh_windows)
        self.view_menu.addAction(refresh_action)

        self.main_window.setMenuBar(self.menubar)

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

    def _make_visuals(self):
        visuals = []
        try:
            while True:
                visuals = self.visual_queue.get_nowait()
        except queue.Empty: # skip to most recent visuals to display
            pass

        for vis in visuals:
            self._update_visual(vis)

        self.mdi_area.tileSubWindows()
        self.main_window._setup_state(self.workflow.stages, visuals)

    def _make_widgets(self, display_controls):
        self.main_window = ViewQtWindow(self.exit_event)
        self.mdi_area = QtWidgets.QMdiArea(self.main_window)
        self.config_dock = QtWidgets.QDockWidget('Options', self.main_window)
        self.config_dock.setObjectName('config_dock')
        self.config_widget = QtWidgets.QFrame(self.config_dock)
        self.config_dock.setWidget(self.config_widget)

        self.main_window.setCentralWidget(self.mdi_area)
        self.main_window.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.config_dock)

        if not display_controls:
            self.config_dock.close()

        self._make_config_widgets()
        self._make_visuals()
        self.main_window.show()
        self.main_window._load_state()

    def _refresh_windows(self):
        self.main_window._save_state()
        self._visual_cache.clear()
        self.mdi_area.closeAllSubWindows()
        self._currently_refreshing = True
        self.rerun_event.set()

    def _rerun(self, arg, stage, value, eval_first=False):
        if eval_first:
            value = eval(value)

        stage.arguments[arg.name] = value

        self.rerun_event.set()

    def _save_json(self):
        settings = QtCore.QSettings('flowws-analysis', 'ViewQt')
        dirname = settings.value('save_menu/last_directory')
        (fname, _) = QtWidgets.QFileDialog.getSaveFileName(
            self.main_window, 'Save Workflow', dirname, filter='*.json')

        if not fname:
            return

        description = self.workflow.to_JSON()
        with open(fname, 'w') as output:
            json.dump(description, output, skipkeys=True)
        settings.setValue('save_menu/last_directory', os.path.dirname(fname))

    def _setup_mdi_subwindow(self, window):
        window.setWindowFlags(QtCore.Qt.CustomizeWindowHint |
                              QtCore.Qt.WindowMinMaxButtonsHint |
                              QtCore.Qt.WindowTitleHint)
        window.show()

    def _update_stage_config(self):
        if not self.stage_event.is_set():
            return

        self.stage_event.clear()
        # TODO cache some of these things instead of constantly recreating
        self._make_config_widgets()

    def _update_visual(self, vis):
        if hasattr(vis, 'draw_matplotlib'):
            from matplotlib.backends.backend_qt5agg import FigureCanvas
            from matplotlib.figure import Figure

            if vis not in self._visual_cache:
                fig = self._visual_cache[vis] = Figure(dpi=72)
                canvas = FigureCanvas(fig)
                window = self.mdi_area.addSubWindow(canvas)
                self._setup_mdi_subwindow(window)

            fig = self._visual_cache[vis]
            fig.clear()
            vis.draw_matplotlib(fig)
            fig.canvas.draw_idle()

        elif hasattr(vis, 'draw_plato'):
            import vispy, vispy.app
            vispy.app.use_app(Qt.__binding__)
            import plato.draw.vispy as draw
            basic_scene = vis.draw_plato()

            if vis not in self._visual_cache:
                canvas_kwargs = dict(config=dict(samples=4))
                scene = self._visual_cache[vis] = basic_scene.convert(
                    draw, canvas_kwargs=canvas_kwargs, clip_scale=8)
                window = self.mdi_area.addSubWindow(scene._canvas.native)
                self._setup_mdi_subwindow(window)

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

    def _update_visuals(self):
        visuals = []
        try:
            while True:
                visuals = self.visual_queue.get_nowait()
        except queue.Empty: # skip to most recent visuals to display
            pass

        for vis in visuals:
            self._update_visual(vis)

        if visuals:
            self.main_window._setup_state(self.workflow.stages, visuals)

        if self._currently_refreshing:
            self._currently_refreshing = False
            self.main_window._load_state()

class RerunThread(threading.Thread):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.args = kwargs['args']

    def run(self):
        (scope, workflow, rerun_event, stage_event, exit_event, visual_queue,
         display_controls) = \
            self.args

        while True:
            try:
                rerun_event.wait(1e-2)
                if rerun_event.is_set():
                    rerun_event.clear()
                    workflow.run()
                    stage_event.set()
                    visual_queue.put(scope.get('visuals', []))
            except KeyboardInterrupt:
                exit_event.set()
            except Exception as e:
                msg = traceback.format_exc(3)
                logger.error(msg)

            if exit_event.is_set():
                break

def sigint_handler(exit_event, *args):
    exit_event.set()

@flowws.add_stage_arguments
class ViewQt(flowws.Stage):
    """Provide an interactive view of the entire workflow using Qt.

    An interactive display window will be opened that displays visual
    results while allowing the arguments of all stages in the workflow
    to be modified.
    """
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
        """Displays parameters and outputs for the workflow in a Qt window."""
        self.workflow = scope['workflow']

        if self._running_threads is None:
            our_sigint_handler = functools.partial(sigint_handler, self._exit_event)
            signal.signal(signal.SIGINT, our_sigint_handler)

            args = (scope, self.workflow, self._rerun_event,
                    self._stage_event, self._exit_event, self._visual_queue,
                    self.arguments['controls'])
            self._visual_queue.put(scope.get('visuals', []))
            self._running_threads = rerun_thread = RerunThread(args=args)
            rerun_thread.start()

            app = ViewQtApp(
                self.workflow, self._rerun_event,
                self._stage_event, self._exit_event, self._visual_queue,
                self.arguments['controls'], [])
            app.exec_()

            rerun_thread.join()
